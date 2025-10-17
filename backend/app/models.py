from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text, JSON
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    role = Column(String, default="Candidate")  # Admin | Interviewer | Candidate
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)  # Junior | Mid | Senior
    type = Column(String, index=True, nullable=False)   # Technical | Behavioral | System Design | Coding
    question_text = Column(String, nullable=False)


class InterviewSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    role = Column(String, nullable=False)
    level = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class TranscriptItem(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True, nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    sentiment_label = Column(String, nullable=True)
    sentiment_score = Column(String, nullable=True)
    bias_flagged = Column(Boolean, default=False)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True, nullable=False)
    summary_text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)
    analysis_type = Column(String, nullable=False)  # unified, sentiment, bias
    result_data = Column(JSON, nullable=False)  # Store the full analysis result
    flagged = Column(Boolean, default=False)  # Whether this analysis flagged any issues
    created_at = Column(DateTime(timezone=True), server_default=func.now())


