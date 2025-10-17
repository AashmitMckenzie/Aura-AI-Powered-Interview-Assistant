from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    role: Optional[str] = "Candidate"


class UserCreate(UserBase):
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_approved: bool
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminCreateRequest(BaseModel):
    email: EmailStr
    password: str


class UserApprovalStatus(BaseModel):
    is_approved: bool
    message: str


class QuestionBase(BaseModel):
    role: str
    level: str
    type: str
    question_text: str


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    role: Optional[str] = None
    level: Optional[str] = None
    type: Optional[str] = None
    question_text: Optional[str] = None


class QuestionOut(QuestionBase):
    id: int

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    user_id: int
    role: str
    level: str


class SessionOut(BaseModel):
    id: int
    user_id: int
    role: str
    level: str

    class Config:
        from_attributes = True


class TranscriptIn(BaseModel):
    session_id: int
    timestamp_ms: int
    text: str
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[str] = None
    bias_flagged: Optional[bool] = None


class TranscriptOut(TranscriptIn):
    id: int

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    session_id: int


class ReportOut(BaseModel):
    id: int
    session_id: int
    summary_text: str

    class Config:
        from_attributes = True


