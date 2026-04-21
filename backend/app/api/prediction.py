from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor, get_current_user
from app.services.grade_prediction import train_model, predict_score
from pydantic import BaseModel

router = APIRouter(prefix="/predict", tags=["prediction"])

class PredictRequest(BaseModel):
    text: str
    max_marks: int

@router.post("/train")
def train(db: Session = Depends(get_db), user=Depends(require_instructor)):
    result = train_model(db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/score")
def predict(data: PredictRequest, user=Depends(get_current_user)):
    result = predict_score(data.text, data.max_marks)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
