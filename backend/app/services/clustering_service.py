import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sentence_transformers import SentenceTransformer
from scipy.stats import pearsonr
from sqlalchemy.orm import Session
from app.models.exam import AnswerExtraction, AIGrade, FinalGrade, Question
import re

model = SentenceTransformer('all-MiniLM-L6-v2')

INVALID_TEXTS = ["No text extracted", "[Error: Rate limit exceeded after all retries]"]

def get_valid_extractions(exam_id: int, db: Session):
    extractions = db.query(AnswerExtraction).join(
        Question, AnswerExtraction.question_id == Question.id
    ).filter(Question.exam_id == exam_id).all()

    valid = []
    for e in extractions:
        if e.extracted_text and e.extracted_text not in INVALID_TEXTS and e.ai_grade:
            valid.append(e)
    return valid

def cluster_answers(exam_id: int, db: Session, n_clusters: int = 3) -> dict:
    extractions = get_valid_extractions(exam_id, db)

    if len(extractions) < n_clusters:
        return {"error": f"Need at least {n_clusters} valid answers to cluster. Have {len(extractions)}."}

    texts = [e.extracted_text for e in extractions]
    embeddings = model.encode(texts)

    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings_scaled)

    cluster_results = []
    for i, (extraction, label) in enumerate(zip(extractions, labels)):
        ai_grade = extraction.ai_grade
        final = ai_grade.final_grade
        score = final.final_score if final and final.final_score is not None else ai_grade.total_score
        max_marks = ai_grade.max_marks
        percentage = (score / max_marks * 100) if max_marks > 0 else 0

        cluster_results.append({
            "student_name": extraction.submission.student_name,
            "student_id": extraction.submission.student_id,
            "question": extraction.question.question_text[:80],
            "answer_preview": extraction.extracted_text[:100],
            "cluster": int(label),
            "score": score,
            "max_marks": max_marks,
            "percentage": round(percentage, 2)
        })

    cluster_summary = {}
    for i in range(n_clusters):
        cluster_items = [r for r in cluster_results if r["cluster"] == i]
        if cluster_items:
            avg_pct = np.mean([r["percentage"] for r in cluster_items])
            if avg_pct >= 70:
                quality = "High Quality"
            elif avg_pct >= 40:
                quality = "Partial Understanding"
            else:
                quality = "Needs Improvement"
            cluster_summary[i] = {
                "quality_label": quality,
                "count": len(cluster_items),
                "avg_percentage": round(float(avg_pct), 2)
            }

    return {
        "exam_id": exam_id,
        "total_answers_clustered": len(extractions),
        "n_clusters": n_clusters,
        "cluster_summary": cluster_summary,
        "results": cluster_results
    }

def correlation_analysis(exam_id: int, db: Session) -> dict:
    extractions = get_valid_extractions(exam_id, db)

    if len(extractions) < 3:
        return {"error": f"Need at least 3 valid answers. Have {len(extractions)}."}

    results_by_question = {}

    for extraction in extractions:
        question_id = extraction.question_id
        question_text = extraction.question.question_text
        text = extraction.extracted_text
        ai_grade = extraction.ai_grade
        final = ai_grade.final_grade
        score = final.final_score if final and final.final_score is not None else ai_grade.total_score
        max_marks = ai_grade.max_marks
        percentage = (score / max_marks * 100) if max_marks > 0 else 0

        word_count = len(text.split())
        char_count = len(text)
        sentence_count = len(re.findall(r'[.!?]+', text)) + 1
        has_formula = 1 if re.search(r'[A-Za-z]\s*=\s*[A-Za-z0-9]', text) else 0

        if question_id not in results_by_question:
            results_by_question[question_id] = {
                "question_text": question_text,
                "word_counts": [],
                "char_counts": [],
                "sentence_counts": [],
                "has_formula": [],
                "scores": [],
                "percentages": []
            }

        results_by_question[question_id]["word_counts"].append(word_count)
        results_by_question[question_id]["char_counts"].append(char_count)
        results_by_question[question_id]["sentence_counts"].append(sentence_count)
        results_by_question[question_id]["has_formula"].append(has_formula)
        results_by_question[question_id]["scores"].append(score)
        results_by_question[question_id]["percentages"].append(percentage)

    correlation_results = []
    for question_id, data in results_by_question.items():
        if len(data["scores"]) < 3:
            continue

        scores = np.array(data["percentages"])
        word_counts = np.array(data["word_counts"])
        char_counts = np.array(data["char_counts"])

        try:
            word_corr, word_p = pearsonr(word_counts, scores)
            char_corr, char_p = pearsonr(char_counts, scores)
        except:
            word_corr, word_p = 0, 1
            char_corr, char_p = 0, 1

        scatter_data = [
            {
                "word_count": int(data["word_counts"][i]),
                "score_percentage": round(data["percentages"][i], 2),
                "student": f"Student {i+1}"
            }
            for i in range(len(data["scores"]))
        ]

        correlation_results.append({
            "question_id": question_id,
            "question_text": data["question_text"][:80],
            "word_length_correlation": round(float(word_corr), 3),
            "word_length_p_value": round(float(word_p), 3),
            "char_length_correlation": round(float(char_corr), 3),
            "interpretation": "Strong positive" if word_corr > 0.6 else "Moderate" if word_corr > 0.3 else "Weak",
            "scatter_data": scatter_data
        })

    return {
        "exam_id": exam_id,
        "correlation_analysis": correlation_results
    }

def semantic_similarity_to_model(
    exam_id: int,
    question_id: int,
    model_answer: str,
    db: Session
) -> dict:
    from sklearn.metrics.pairwise import cosine_similarity

    extractions = db.query(AnswerExtraction).filter(
        AnswerExtraction.question_id == question_id
    ).all()

    valid = [e for e in extractions if e.extracted_text and e.extracted_text not in INVALID_TEXTS]

    if not valid:
        return {"error": "No valid answers found for this question"}

    model_embedding = model.encode([model_answer])
    student_texts = [e.extracted_text for e in valid]
    student_embeddings = model.encode(student_texts)

    similarities = cosine_similarity(student_embeddings, model_embedding).flatten()

    results = []
    for i, extraction in enumerate(valid):
        ai_grade = extraction.ai_grade
        score = 0
        if ai_grade:
            final = ai_grade.final_grade
            score = final.final_score if final and final.final_score is not None else ai_grade.total_score

        results.append({
            "student_name": extraction.submission.student_name,
            "student_id": extraction.submission.student_id,
            "semantic_similarity": round(float(similarities[i]), 3),
            "current_score": score,
            "answer_preview": extraction.extracted_text[:150]
        })

    results.sort(key=lambda x: x["semantic_similarity"], reverse=True)

    return {
        "question_id": question_id,
        "model_answer_preview": model_answer[:100],
        "results": results,
        "avg_similarity": round(float(np.mean(similarities)), 3),
        "highest_similarity": round(float(np.max(similarities)), 3),
        "lowest_similarity": round(float(np.min(similarities)), 3)
    }
