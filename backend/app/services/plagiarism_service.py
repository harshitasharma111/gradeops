from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sqlalchemy.orm import Session
from app.models.exam import AnswerExtraction, StudentSubmission, PlagiarismFlag, Question
from typing import List

model = SentenceTransformer('all-MiniLM-L6-v2')

SIMILARITY_THRESHOLD = 0.85

def detect_plagiarism_for_question(
    question_id: int,
    exam_id: int,
    db: Session
) -> List[dict]:
    extractions = db.query(AnswerExtraction).filter(
        AnswerExtraction.question_id == question_id
    ).all()

    valid = [
        e for e in extractions
        if e.extracted_text and
        e.extracted_text not in ["No text extracted", "[Error: Rate limit exceeded after all retries]"]
    ]

    if len(valid) < 2:
        return []

    texts = [e.extracted_text for e in valid]
    embeddings = model.encode(texts)
    similarity_matrix = cosine_similarity(embeddings)

    flags = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            score = float(similarity_matrix[i][j])
            if score >= SIMILARITY_THRESHOLD:
                existing = db.query(PlagiarismFlag).filter(
                    PlagiarismFlag.question_id == question_id,
                    PlagiarismFlag.submission_1_id == valid[i].submission_id,
                    PlagiarismFlag.submission_2_id == valid[j].submission_id
                ).first()

                if not existing:
                    flag = PlagiarismFlag(
                        exam_id=exam_id,
                        question_id=question_id,
                        submission_1_id=valid[i].submission_id,
                        submission_2_id=valid[j].submission_id,
                        similarity_score=score
                    )
                    db.add(flag)
                    db.commit()
                    db.refresh(flag)

                sub1 = db.query(StudentSubmission).filter(
                    StudentSubmission.id == valid[i].submission_id
                ).first()
                sub2 = db.query(StudentSubmission).filter(
                    StudentSubmission.id == valid[j].submission_id
                ).first()

                flags.append({
                    "question_id": question_id,
                    "student_1": sub1.student_name if sub1 else "Unknown",
                    "student_1_id": sub1.student_id if sub1 else "Unknown",
                    "student_2": sub2.student_name if sub2 else "Unknown",
                    "student_2_id": sub2.student_id if sub2 else "Unknown",
                    "similarity_score": round(score, 4),
                    "answer_1": valid[i].extracted_text[:200],
                    "answer_2": valid[j].extracted_text[:200]
                })

    return flags

def run_plagiarism_check(exam_id: int, db: Session) -> dict:
    from app.models.exam import Exam
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"error": "Exam not found"}

    all_flags = []
    for question in exam.questions:
        flags = detect_plagiarism_for_question(
            question_id=question.id,
            exam_id=exam_id,
            db=db
        )
        all_flags.extend(flags)

    return {
        "exam_id": exam_id,
        "total_flags": len(all_flags),
        "flags": all_flags
    }
