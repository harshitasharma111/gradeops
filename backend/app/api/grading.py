from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor, get_current_user
from app.models.exam import AnswerExtraction, AIGrade, FinalGrade, StudentSubmission, SubmissionStatus
from app.services.grading_agent import grade_answer
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(prefix="/grade", tags=["grading"])

@router.post("/submission/{submission_id}")
def grade_submission(submission_id: int, db: Session = Depends(get_db), user=Depends(require_instructor)):
    submission = db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    extractions = db.query(AnswerExtraction).filter(AnswerExtraction.submission_id == submission_id).all()
    if not extractions:
        raise HTTPException(status_code=400, detail="No extracted answers found. Run OCR first.")

    results = []
    for extraction in extractions:
        question = extraction.question
        rubric = {
            "max_marks": question.max_marks,
            "conditions": [
                {"condition": rc.condition_text, "marks": rc.marks}
                for rc in question.rubric_conditions
            ]
        }

        grade_result = grade_answer(
            question=question.question_text,
            student_answer=extraction.extracted_text,
            rubric=rubric
        )

        existing_grade = db.query(AIGrade).filter(AIGrade.extraction_id == extraction.id).first()
        if existing_grade:
            db.delete(existing_grade)
            db.commit()

        ai_grade = AIGrade(
            extraction_id=extraction.id,
            total_score=grade_result["total_score"],
            max_marks=grade_result["max_marks"],
            justification=grade_result["justification"],
            confidence=grade_result["confidence"],
            needs_urgent_review=grade_result["needs_urgent_review"],
            condition_breakdown=json.dumps(grade_result["condition_breakdown"])
        )
        db.add(ai_grade)
        db.commit()
        db.refresh(ai_grade)

        final_grade = FinalGrade(
            ai_grade_id=ai_grade.id,
            final_score=grade_result["total_score"],
            status="pending"
        )
        db.add(final_grade)
        db.commit()

        results.append({
            "question": question.question_text,
            "extracted_answer": extraction.extracted_text,
            "score": grade_result["total_score"],
            "max_marks": grade_result["max_marks"],
            "justification": grade_result["justification"],
            "confidence": grade_result["confidence"],
            "needs_urgent_review": grade_result["needs_urgent_review"]
        })

    submission.status = SubmissionStatus.graded
    db.commit()

    return {
        "submission_id": submission_id,
        "student_name": submission.student_name,
        "results": results
    }

@router.get("/submission/{submission_id}/results")
def get_grading_results(submission_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    extractions = db.query(AnswerExtraction).filter(AnswerExtraction.submission_id == submission_id).all()
    if not extractions:
        raise HTTPException(status_code=404, detail="No results found")

    results = []
    for extraction in extractions:
        ai_grade = extraction.ai_grade
        if ai_grade:
            results.append({
                "question": extraction.question.question_text,
                "extracted_answer": extraction.extracted_text,
                "score": ai_grade.total_score,
                "max_marks": ai_grade.max_marks,
                "justification": ai_grade.justification,
                "confidence": ai_grade.confidence,
                "needs_urgent_review": ai_grade.needs_urgent_review,
                "condition_breakdown": json.loads(ai_grade.condition_breakdown) if ai_grade.condition_breakdown else [],
                "final_grade_status": ai_grade.final_grade.status if ai_grade.final_grade else "pending"
            })

    return {"submission_id": submission_id, "results": results}

@router.post("/review/{ai_grade_id}")
def review_grade(
    ai_grade_id: int,
    action: str,
    override_score: Optional[float] = None,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    ai_grade = db.query(AIGrade).filter(AIGrade.id == ai_grade_id).first()
    if not ai_grade:
        raise HTTPException(status_code=404, detail="Grade not found")

    final_grade = ai_grade.final_grade
    if not final_grade:
        raise HTTPException(status_code=404, detail="Final grade record not found")

    if action == "approve":
        final_grade.status = "approved"
        final_grade.final_score = ai_grade.total_score
    elif action == "override":
        if override_score is None:
            raise HTTPException(status_code=400, detail="override_score required")
        final_grade.status = "overridden"
        final_grade.final_score = override_score
    else:
        raise HTTPException(status_code=400, detail="action must be approve or override")

    final_grade.reviewed_by = user.id
    final_grade.ta_comment = comment
    final_grade.reviewed_at = datetime.utcnow()
    db.commit()

    return {"message": f"Grade {action}d successfully", "final_score": final_grade.final_score}

@router.get("/pending-reviews")
def get_pending_reviews(db: Session = Depends(get_db), user=Depends(get_current_user)):
    pending = db.query(FinalGrade).filter(FinalGrade.status == "pending").all()
    results = []
    for fg in pending:
        ai_grade = fg.ai_grade
        extraction = ai_grade.extraction
        submission = extraction.submission
        question = extraction.question
        results.append({
            "ai_grade_id": ai_grade.id,
            "final_grade_id": fg.id,
            "student_name": submission.student_name,
            "student_id": submission.student_id,
            "question": question.question_text,
            "extracted_answer": extraction.extracted_text,
            "ai_score": ai_grade.total_score,
            "max_marks": ai_grade.max_marks,
            "justification": ai_grade.justification,
            "confidence": ai_grade.confidence,
            "needs_urgent_review": ai_grade.needs_urgent_review
        })
    return results
