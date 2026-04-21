from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor, get_current_user
from app.services.analytics_service import get_exam_analytics, export_grades_to_dataframe
from app.services.plagiarism_service import run_plagiarism_check
from app.models.exam import PlagiarismFlag
import io

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/exam/{exam_id}")
def exam_analytics(exam_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = get_exam_analytics(exam_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/exam/{exam_id}/plagiarism")
def check_plagiarism(exam_id: int, db: Session = Depends(get_db), user=Depends(require_instructor)):
    result = run_plagiarism_check(exam_id, db)
    return result

@router.get("/exam/{exam_id}/plagiarism-flags")
def get_plagiarism_flags(exam_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    flags = db.query(PlagiarismFlag).filter(PlagiarismFlag.exam_id == exam_id).all()
    return [
        {
            "flag_id": f.id,
            "question_id": f.question_id,
            "submission_1_id": f.submission_1_id,
            "submission_2_id": f.submission_2_id,
            "similarity_score": f.similarity_score
        }
        for f in flags
    ]

@router.get("/exam/{exam_id}/export")
def export_grades(exam_id: int, db: Session = Depends(get_db), user=Depends(require_instructor)):
    df = export_grades_to_dataframe(exam_id, db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data to export")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Grades')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_grades.xlsx"}
    )
