from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    instructor_id = Column(Integer, ForeignKey("users.id"))

    instructor = relationship("User", backref="courses")
    exams = relationship("Exam", backref="course")
    assignments = relationship("CourseAssignment", backref="course")

class CourseAssignment(Base):
    __tablename__ = "course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    ta_id = Column(Integer, ForeignKey("users.id"))
