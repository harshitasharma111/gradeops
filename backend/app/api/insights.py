from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_instructor
from app.services.clustering_service import cluster_answers, correlation_analysis, semantic_similarity_to_model
from pydantic import BaseModel

router = APIRouter(prefix="/insights", tags=["insights"])

class ModelAnswerRequest(BaseModel):
    question_id: int
    model_answer: str

@router.get("/exam/{exam_id}/clusters")
def get_clusters(exam_id: int, n_clusters: int = 3, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = cluster_answers(exam_id, db, n_clusters)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/exam/{exam_id}/correlations")
def get_correlations(exam_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = correlation_analysis(exam_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/exam/{exam_id}/model-answer-similarity")
def model_answer_similarity(exam_id: int, data: ModelAnswerRequest, db: Session = Depends(get_db), user=Depends(require_instructor)):
    result = semantic_similarity_to_model(exam_id, data.question_id, data.model_answer, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
