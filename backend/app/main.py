from fastapi import FastAPI, Depends
from app.core.database import engine
from app.core.dependencies import require_instructor, require_ta
from app.api.auth import router as auth_router
from app.api.exams import router as exam_router

app = FastAPI(title="GradeOps API", version="1.0.0")
app.include_router(auth_router)
app.include_router(exam_router)

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

@app.get("/instructor/dashboard")
def instructor_dashboard(user=Depends(require_instructor)):
    return {"message": f"Welcome Instructor {user.name}"}

@app.get("/ta/dashboard")
def ta_dashboard(user=Depends(require_ta)):
    return {"message": f"Welcome TA {user.name}"}
