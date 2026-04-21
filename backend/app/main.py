from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
from app.api.auth import router as auth_router
from app.api.exams import router as exam_router
from app.api.courses import router as course_router
from app.api.grading import router as grading_router
from app.api.analytics import router as analytics_router
from app.api.prediction import router as prediction_router
from app.api.insights import router as insights_router

app = FastAPI(title="GradeOps API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(exam_router)
app.include_router(course_router)
app.include_router(grading_router)
app.include_router(analytics_router)
app.include_router(prediction_router)
app.include_router(insights_router)

@app.on_event("startup")
def startup():
    try:
        conn = engine.connect()
        conn.close()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

@app.get("/")
def root():
    return {"message": "GradeOps API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}
