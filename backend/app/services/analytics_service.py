import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.exam import Exam, Question, StudentSubmission, AnswerExtraction, AIGrade, FinalGrade
from typing import List, Dict
import json

def get_exam_analytics(exam_id: int, db: Session) -> dict:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"error": "Exam not found"}

    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id
    ).all()

    if not submissions:
        return {"error": "No submissions found"}

    student_totals = []
    question_stats = []

    for question in sorted(exam.questions, key=lambda x: x.order_number):
        scores = []
        override_count = 0
        total_reviewed = 0

        for submission in submissions:
            extraction = db.query(AnswerExtraction).filter(
                AnswerExtraction.submission_id == submission.id,
                AnswerExtraction.question_id == question.id
            ).first()

            if extraction and extraction.ai_grade:
                ai_grade = extraction.ai_grade
                final_grade = ai_grade.final_grade

                if final_grade:
                    scores.append(final_grade.final_score)
                    total_reviewed += 1
                    if final_grade.status == "overridden":
                        override_count += 1
                else:
                    scores.append(ai_grade.total_score)

        if scores:
            scores_array = np.array(scores)
            question_stats.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "max_marks": question.max_marks,
                "avg_score": round(float(np.mean(scores_array)), 2),
                "median_score": round(float(np.median(scores_array)), 2),
                "std_dev": round(float(np.std(scores_array)), 2),
                "min_score": round(float(np.min(scores_array)), 2),
                "max_score": round(float(np.max(scores_array)), 2),
                "difficulty_index": round(float(np.mean(scores_array)) / question.max_marks, 2),
                "override_rate": round(override_count / total_reviewed, 2) if total_reviewed > 0 else 0,
                "score_distribution": list(scores_array)
            })

    for submission in submissions:
        total_score = 0
        max_possible = 0
        for question in exam.questions:
            extraction = db.query(AnswerExtraction).filter(
                AnswerExtraction.submission_id == submission.id,
                AnswerExtraction.question_id == question.id
            ).first()
            max_possible += question.max_marks
            if extraction and extraction.ai_grade:
                final = extraction.ai_grade.final_grade
                if final:
                    total_score += final.final_score or 0
                else:
                    total_score += extraction.ai_grade.total_score or 0

        student_totals.append({
            "student_name": submission.student_name,
            "student_id": submission.student_id,
            "total_score": round(total_score, 2),
            "max_possible": max_possible,
            "percentage": round((total_score / max_possible * 100), 2) if max_possible > 0 else 0
        })

    if student_totals:
        percentages = [s["percentage"] for s in student_totals]
        percentages_array = np.array(percentages)
        class_stats = {
            "total_students": len(student_totals),
            "class_average": round(float(np.mean(percentages_array)), 2),
            "class_median": round(float(np.median(percentages_array)), 2),
            "class_std_dev": round(float(np.std(percentages_array)), 2),
            "highest_score": round(float(np.max(percentages_array)), 2),
            "lowest_score": round(float(np.min(percentages_array)), 2),
            "pass_rate": round(len([p for p in percentages if p >= 40]) / len(percentages) * 100, 2)
        }
    else:
        class_stats = {}

    return {
        "exam_id": exam_id,
        "exam_title": exam.title,
        "class_statistics": class_stats,
        "question_analytics": question_stats,
        "student_scores": student_totals
    }

def export_grades_to_dataframe(exam_id: int, db: Session) -> pd.DataFrame:
    analytics = get_exam_analytics(exam_id, db)
    if "error" in analytics:
        return pd.DataFrame()

    rows = []
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id
    ).all()

    for submission in submissions:
        row = {
            "Student Name": submission.student_name,
            "Student ID": submission.student_id,
        }
        total = 0
        for question in sorted(exam.questions, key=lambda x: x.order_number):
            extraction = db.query(AnswerExtraction).filter(
                AnswerExtraction.submission_id == submission.id,
                AnswerExtraction.question_id == question.id
            ).first()
            score = 0
            status = "not graded"
            if extraction and extraction.ai_grade:
                final = extraction.ai_grade.final_grade
                if final:
                    score = final.final_score or 0
                    status = final.status
                else:
                    score = extraction.ai_grade.total_score or 0
                    status = "pending"
            row[f"Q{question.order_number} Score"] = score
            row[f"Q{question.order_number} Max"] = question.max_marks
            row[f"Q{question.order_number} Status"] = status
            total += score
        row["Total Score"] = total
        rows.append(row)

    return pd.DataFrame(rows)
