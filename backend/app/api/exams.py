from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor
from app.models.exam import Exam
import shutil
import os

router = APIRouter(prefix="/exams", tags=["exams"])

STORAGE_PATH = "/Users/harshitasharma/GradeOps CC/gradeops/storage/exams"

@router.post("/upload")
def upload_exam(
    student_name: str = Form(...),
    student_id: str = Form(...),
    course: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_instructor)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(STORAGE_PATH, f"{student_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    exam = Exam(
        student_name=student_name,
        student_id=student_id,
        course=course,
        file_path=file_path,
        uploaded_by=user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    return {
        "message": "Exam uploaded successfully",
        "exam_id": exam.id,
        "student": student_name,
        "course": course,
        "status": exam.status
    }

@router.get("/list")
def list_exams(db: Session = Depends(get_db), user=Depends(require_instructor)):
    exams = db.query(Exam).filter(Exam.uploaded_by == user.id).all()
    return [
        {
            "exam_id": e.id,
            "student_name": e.student_name,
            "student_id": e.student_id,
            "course": e.course,
            "status": e.status,
            "uploaded_at": e.uploaded_at
        }
        for e in exams
    ]
