from fastapi import FastAPI
from app.core.database import engine
from app.api.auth import router as auth_router

app = FastAPI(title="GradeOps API", version="1.0.0")
app.include_router(auth_router)

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
