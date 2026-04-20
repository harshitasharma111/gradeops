from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime

class ExamStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    graded = "graded"
    reviewed = "reviewed"

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False)
    student_id = Column(String, nullable=False)
    course = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(Enum(ExamStatus), default=ExamStatus.uploaded)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"))

    uploader = relationship("User", backref="exams")
