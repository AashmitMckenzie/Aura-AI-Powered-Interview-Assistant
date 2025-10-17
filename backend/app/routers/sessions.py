from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..security import get_current_user
from ..security_utils import SecurityUtils


router = APIRouter()


@router.post("/", response_model=schemas.SessionOut)
def create_session(payload: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Security: Validate user can only create sessions for themselves
    if current_user.id != payload.user_id:
        raise HTTPException(status_code=403, detail="You can only create sessions for yourself")
    
    session = models.InterviewSession(
        user_id=payload.user_id, role=payload.role, level=payload.level
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=schemas.SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    s = db.query(models.InterviewSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security: Validate user can only access their own sessions
    SecurityUtils.validate_session_ownership(current_user.id, s.user_id)
    return s


@router.post("/transcript", response_model=schemas.TranscriptOut)
def add_transcript(payload: schemas.TranscriptIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    s = db.query(models.InterviewSession).get(payload.session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security: Validate user can only add transcripts to their own sessions
    SecurityUtils.validate_session_ownership(current_user.id, s.user_id)
    
    # Security: Sanitize input text
    sanitized_text = SecurityUtils.sanitize_input(payload.text)
    
    t = models.TranscriptItem(
        session_id=payload.session_id,
        timestamp_ms=payload.timestamp_ms,
        text=sanitized_text,
        sentiment_label=payload.sentiment_label,
        sentiment_score=payload.sentiment_score,
        bias_flagged=payload.bias_flagged or False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("/{session_id}/transcript", response_model=List[schemas.TranscriptOut])
def list_transcript(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Security: Validate session ownership
    session = db.query(models.InterviewSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    SecurityUtils.validate_session_ownership(current_user.id, session.user_id)
    
    return db.query(models.TranscriptItem).filter(models.TranscriptItem.session_id == session_id).order_by(models.TranscriptItem.timestamp_ms.asc()).all()


@router.post("/{session_id}/end")
def end_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """End an interview session"""
    session = db.query(models.InterviewSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security: Validate user can only end their own sessions
    SecurityUtils.validate_session_ownership(current_user.id, session.user_id)
    
    # Update session end time
    from datetime import datetime
    session.ended_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Session ended successfully", "session_id": session_id}


@router.get("/{session_id}/full-transcript")
def get_full_transcript(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Get complete transcript for a session, combining all text"""
    session = db.query(models.InterviewSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security: Validate user can only access their own session transcripts
    SecurityUtils.validate_session_ownership(current_user.id, session.user_id)
    
    # Get all transcript items ordered by timestamp
    transcript_items = db.query(models.TranscriptItem).filter(
        models.TranscriptItem.session_id == session_id
    ).order_by(models.TranscriptItem.timestamp_ms.asc()).all()
    
    # Combine all text into a single transcript
    full_text = " ".join([item.text for item in transcript_items if item.text.strip()])
    
    return {
        "session_id": session_id,
        "total_items": len(transcript_items),
        "full_transcript": full_text,
        "transcript_items": transcript_items
    }


