from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor
from app.services.grading_agent import grade_answer
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/grade", tags=["grading"])

class RubricCondition(BaseModel):
    condition: str
    marks: int

class RubricSchema(BaseModel):
    max_marks: int
    conditions: List[RubricCondition]

class GradeRequest(BaseModel):
    question: str
    student_answer: str
    rubric: RubricSchema

@router.post("/answer")
def grade_student_answer(
    request: GradeRequest,
    user=Depends(require_instructor)
):
    rubric_dict = {
        "max_marks": request.rubric.max_marks,
        "conditions": [c.dict() for c in request.rubric.conditions]
    }

    result = grade_answer(
        question=request.question,
        student_answer=request.student_answer,
        rubric=rubric_dict
    )

    return result
