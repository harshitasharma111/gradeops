import numpy as np
from sqlalchemy.orm import Session
from app.models.exam import AIGrade, FinalGrade, RubricCondition, AnswerExtraction, Question

def confidence_calibration(exam_id: int, db: Session) -> dict:
    from app.models.exam import Exam
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"error": "Exam not found"}

    ai_grades = db.query(AIGrade).join(
        AnswerExtraction, AIGrade.extraction_id == AnswerExtraction.id
    ).join(
        Question, AnswerExtraction.question_id == Question.id
    ).filter(Question.exam_id == exam_id).all()

    reviewed = [g for g in ai_grades if g.final_grade and g.final_grade.status in ["approved", "overridden"]]

    if len(reviewed) < 3:
        return {"error": f"Need at least 3 reviewed grades for calibration. Have {len(reviewed)}."}

    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.01]
    bin_labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    bin_data = {label: {"total": 0, "approved": 0, "avg_confidence": 0, "confidences": []} for label in bin_labels}

    for grade in reviewed:
        confidence = grade.confidence
        is_approved = grade.final_grade.status == "approved"

        for i in range(len(bins) - 1):
            if bins[i] <= confidence < bins[i + 1]:
                label = bin_labels[i]
                bin_data[label]["total"] += 1
                bin_data[label]["confidences"].append(confidence)
                if is_approved:
                    bin_data[label]["approved"] += 1
                break

    calibration_curve = []
    for label in bin_labels:
        data = bin_data[label]
        if data["total"] > 0:
            approval_rate = data["approved"] / data["total"]
            avg_conf = np.mean(data["confidences"])
            calibration_curve.append({
                "confidence_bin": label,
                "avg_confidence": round(float(avg_conf), 3),
                "approval_rate": round(approval_rate, 3),
                "total_samples": data["total"],
                "perfectly_calibrated": round(float(avg_conf), 1)
            })

    total_approved = sum(1 for g in reviewed if g.final_grade.status == "approved")
    overall_approval_rate = total_approved / len(reviewed)
    avg_confidence = np.mean([g.confidence for g in reviewed])

    overconfident = [g for g in reviewed if g.confidence > 0.7 and g.final_grade.status == "overridden"]
    underconfident = [g for g in reviewed if g.confidence < 0.4 and g.final_grade.status == "approved"]

    return {
        "exam_id": exam_id,
        "total_reviewed": len(reviewed),
        "overall_approval_rate": round(overall_approval_rate, 3),
        "avg_ai_confidence": round(float(avg_confidence), 3),
        "overconfident_count": len(overconfident),
        "underconfident_count": len(underconfident),
        "calibration_curve": calibration_curve,
        "interpretation": "Well calibrated" if abs(overall_approval_rate - float(avg_confidence)) < 0.1 else "Needs calibration"
    }

def rubric_optimization(exam_id: int, db: Session) -> dict:
    import json
    from app.models.exam import Exam

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"error": "Exam not found"}

    suggestions = []

    for question in exam.questions:
        conditions = question.rubric_conditions
        extractions = db.query(AnswerExtraction).filter(
            AnswerExtraction.question_id == question.id
        ).all()

        graded_extractions = [e for e in extractions if e.ai_grade]

        if not graded_extractions:
            continue

        condition_stats = {rc.id: {"condition_text": rc.condition_text, "marks": rc.marks, "satisfied_count": 0, "total": 0} for rc in conditions}

        for extraction in graded_extractions:
            if not extraction.ai_grade.condition_breakdown:
                continue
            try:
                breakdown = json.loads(extraction.ai_grade.condition_breakdown)
                for i, rc in enumerate(conditions):
                    if i < len(breakdown):
                        condition_stats[rc.id]["total"] += 1
                        if breakdown[i].get("satisfied", False):
                            condition_stats[rc.id]["satisfied_count"] += 1
            except:
                continue

        question_suggestions = []
        for rc_id, stats in condition_stats.items():
            if stats["total"] == 0:
                continue
            satisfaction_rate = stats["satisfied_count"] / stats["total"]
            if satisfaction_rate < 0.2:
                question_suggestions.append({
                    "condition": stats["condition_text"],
                    "marks": stats["marks"],
                    "satisfaction_rate": round(satisfaction_rate, 2),
                    "severity": "high",
                    "suggestion": f"Only {round(satisfaction_rate*100)}% of students satisfied this condition. Consider simplifying or splitting into smaller conditions.",
                    "flag": "Too strict or unclear"
                })
            elif satisfaction_rate > 0.95:
                question_suggestions.append({
                    "condition": stats["condition_text"],
                    "marks": stats["marks"],
                    "satisfaction_rate": round(satisfaction_rate, 2),
                    "severity": "low",
                    "suggestion": f"{round(satisfaction_rate*100)}% of students satisfied this condition. Consider making it more challenging.",
                    "flag": "Too easy"
                })

        if question_suggestions:
            suggestions.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "suggestions": question_suggestions
            })

    return {
        "exam_id": exam_id,
        "total_questions_analyzed": len(exam.questions),
        "questions_needing_attention": len(suggestions),
        "suggestions": suggestions
    }
