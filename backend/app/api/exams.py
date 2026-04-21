from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor, get_current_user
from app.models.exam import Exam, Question, RubricCondition, StudentSubmission, SubmissionStatus
from app.models.course import Course
from app.services.ocr_service import extract_text_from_pdf
from pydantic import BaseModel
from typing import List
import shutil
import os
import json

router = APIRouter(prefix="/exams", tags=["exams"])

STORAGE_PATH = "/Users/harshitasharma/GradeOps CC/gradeops/storage/exams"

class RubricConditionSchema(BaseModel):
    condition_text: str
    marks: int

class QuestionSchema(BaseModel):
    question_text: str
    max_marks: int
    order_number: int
    rubric_conditions: List[RubricConditionSchema]

class CreateExamRequest(BaseModel):
    title: str
    course_id: int
    questions: List[QuestionSchema]

@router.post("/create")
def create_exam(data: CreateExamRequest, db: Session = Depends(get_db), user=Depends(require_instructor)):
    course = db.query(Course).filter(Course.id == data.course_id, Course.instructor_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    exam = Exam(title=data.title, course_id=data.course_id, created_by=user.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    for q in data.questions:
        question = Question(
            exam_id=exam.id,
            question_text=q.question_text,
            max_marks=q.max_marks,
            order_number=q.order_number
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for rc in q.rubric_conditions:
            condition = RubricCondition(
                question_id=question.id,
                condition_text=rc.condition_text,
                marks=rc.marks
            )
            db.add(condition)

    db.commit()
    return {"message": "Exam created", "exam_id": exam.id, "title": exam.title}

@router.get("/course/{course_id}")
def get_exams_by_course(course_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exams = db.query(Exam).filter(Exam.course_id == course_id).all()
    return [
        {
            "exam_id": e.id,
            "title": e.title,
            "created_at": e.created_at,
            "question_count": len(e.questions),
            "submission_count": len(e.submissions)
        }
        for e in exams
    ]

@router.get("/{exam_id}/details")
def get_exam_details(exam_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return {
        "exam_id": exam.id,
        "title": exam.title,
        "questions": [
            {
                "question_id": q.id,
                "question_text": q.question_text,
                "max_marks": q.max_marks,
                "order_number": q.order_number,
                "rubric_conditions": [
                    {"condition_text": rc.condition_text, "marks": rc.marks}
                    for rc in q.rubric_conditions
                ]
            }
            for q in sorted(exam.questions, key=lambda x: x.order_number)
        ]
    }

@router.post("/{exam_id}/upload-submission")
def upload_submission(
    exam_id: int,
    student_name: str = Form(...),
    student_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_instructor)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(STORAGE_PATH, f"{exam_id}_{student_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    submission = StudentSubmission(
        exam_id=exam_id,
        student_name=student_name,
        student_id=student_id,
        file_path=file_path
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Submission uploaded",
        "submission_id": submission.id,
        "student_name": student_name,
        "status": submission.status
    }

@router.get("/{exam_id}/submissions")
def get_submissions(exam_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    submissions = db.query(StudentSubmission).filter(StudentSubmission.exam_id == exam_id).all()
    return [
        {
            "submission_id": s.id,
            "student_name": s.student_name,
            "student_id": s.student_id,
            "status": s.status,
            "uploaded_at": s.uploaded_at
        }
        for s in submissions
    ]

@router.post("/submissions/{submission_id}/process")
def process_submission(submission_id: int, db: Session = Depends(get_db), user=Depends(require_instructor)):
    submission = db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = SubmissionStatus.processing
    db.commit()

    extracted = extract_text_from_pdf(submission.file_path)

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    questions = sorted(exam.questions, key=lambda x: x.order_number)

    from app.models.exam import AnswerExtraction
    for i, question in enumerate(questions):
        page_key = f"page_{i+1}"
        text = extracted.get(page_key, "No text extracted")
        extraction = AnswerExtraction(
            submission_id=submission.id,
            question_id=question.id,
            extracted_text=text,
            page_number=i+1
        )
        db.add(extraction)

    submission.status = SubmissionStatus.graded
    db.commit()

    return {"message": "Submission processed", "submission_id": submission_id}
