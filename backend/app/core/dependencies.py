from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from jose import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_instructor(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.instructor:
        raise HTTPException(status_code=403, detail="Instructors only")
    return current_user

def require_ta(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ta:
        raise HTTPException(status_code=403, detail="TAs only")
    return current_user
