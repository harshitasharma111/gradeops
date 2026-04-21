from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_instructor, require_ta, get_current_user
from app.models.course import Course, CourseAssignment
from app.models.user import User, UserRole
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/courses", tags=["courses"])

class CreateCourseRequest(BaseModel):
    name: str
    code: str

class AssignTARequest(BaseModel):
    ta_email: str

@router.post("/create")
def create_course(data: CreateCourseRequest, db: Session = Depends(get_db), user=Depends(require_instructor)):
    existing = db.query(Course).filter(Course.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course code already exists")
    course = Course(name=data.name, code=data.code, instructor_id=user.id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": "Course created", "course_id": course.id, "name": course.name, "code": course.code}

@router.get("/my-courses")
def get_my_courses(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role == UserRole.instructor:
        courses = db.query(Course).filter(Course.instructor_id == user.id).all()
    else:
        assignments = db.query(CourseAssignment).filter(CourseAssignment.ta_id == user.id).all()
        course_ids = [a.course_id for a in assignments]
        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
    
    return [
        {"course_id": c.id, "name": c.name, "code": c.code}
        for c in courses
    ]

@router.post("/{course_id}/assign-ta")
def assign_ta(course_id: int, data: AssignTARequest, db: Session = Depends(get_db), user=Depends(require_instructor)):
    course = db.query(Course).filter(Course.id == course_id, Course.instructor_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    ta = db.query(User).filter(User.email == data.ta_email, User.role == UserRole.ta).first()
    if not ta:
        raise HTTPException(status_code=404, detail="TA not found with that email")
    
    existing = db.query(CourseAssignment).filter(
        CourseAssignment.course_id == course_id,
        CourseAssignment.ta_id == ta.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="TA already assigned to this course")
    
    assignment = CourseAssignment(course_id=course_id, ta_id=ta.id)
    db.add(assignment)
    db.commit()
    return {"message": f"TA {ta.name} assigned to {course.name}"}

@router.get("/{course_id}/tas")
def get_course_tas(course_id: int, db: Session = Depends(get_db), user=Depends(require_instructor)):
    assignments = db.query(CourseAssignment).filter(CourseAssignment.course_id == course_id).all()
    tas = [db.query(User).filter(User.id == a.ta_id).first() for a in assignments]
    return [{"ta_id": ta.id, "name": ta.name, "email": ta.email} for ta in tas if ta]
