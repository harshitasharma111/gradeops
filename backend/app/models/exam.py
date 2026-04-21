from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime

class SubmissionStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    graded = "graded"
    reviewed = "reviewed"

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", backref="exam")
    submissions = relationship("StudentSubmission", backref="exam")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    question_text = Column(Text, nullable=False)
    max_marks = Column(Integer, nullable=False)
    order_number = Column(Integer, nullable=False)

    rubric_conditions = relationship("RubricCondition", backref="question")
    extractions = relationship("AnswerExtraction", backref="question")

class RubricCondition(Base):
    __tablename__ = "rubric_conditions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    condition_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)

class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    student_name = Column(String, nullable=False)
    student_id = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.uploaded)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    extractions = relationship("AnswerExtraction", backref="submission")

class AnswerExtraction(Base):
    __tablename__ = "answer_extractions"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("student_submissions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    extracted_text = Column(Text)
    page_number = Column(Integer)

    ai_grade = relationship("AIGrade", backref="extraction", uselist=False)

class AIGrade(Base):
    __tablename__ = "ai_grades"

    id = Column(Integer, primary_key=True, index=True)
    extraction_id = Column(Integer, ForeignKey("answer_extractions.id"))
    total_score = Column(Float)
    max_marks = Column(Integer)
    justification = Column(Text)
    confidence = Column(Float)
    needs_urgent_review = Column(Boolean, default=False)
    condition_breakdown = Column(Text)

    final_grade = relationship("FinalGrade", backref="ai_grade", uselist=False)

class FinalGrade(Base):
    __tablename__ = "final_grades"

    id = Column(Integer, primary_key=True, index=True)
    ai_grade_id = Column(Integer, ForeignKey("ai_grades.id"))
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    final_score = Column(Float)
    ta_comment = Column(Text)
    status = Column(String, default="pending")
    reviewed_at = Column(DateTime)

class PlagiarismFlag(Base):
    __tablename__ = "plagiarism_flags"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    submission_1_id = Column(Integer, ForeignKey("student_submissions.id"))
    submission_2_id = Column(Integer, ForeignKey("student_submissions.id"))
    similarity_score = Column(Float)
