from pydantic import BaseModel, EmailStr
from enum import Enum

class UserRole(str, Enum):
    instructor = "instructor"
    ta = "ta"

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
