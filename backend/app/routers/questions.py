from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..security import get_current_user


router = APIRouter()


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Require admin role for question management"""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=List[schemas.QuestionOut])
def list_questions(
    role: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Question)
    if role:
        query = query.filter(models.Question.role == role)
    if level:
        query = query.filter(models.Question.level == level)
    if type:
        query = query.filter(models.Question.type == type)
    if q:
        query = query.filter(models.Question.question_text.ilike(f"%{q}%"))
    return query.limit(2000).all()


@router.post("/", response_model=schemas.QuestionOut)
def create_question(payload: schemas.QuestionCreate, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    # Security: Validate and sanitize input
    from ..security_utils import SecurityUtils
    
    # Sanitize question text
    sanitized_payload = payload.dict()
    if 'question_text' in sanitized_payload:
        sanitized_payload['question_text'] = SecurityUtils.sanitize_input(sanitized_payload['question_text'])
    
    obj = models.Question(**sanitized_payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{question_id}", response_model=schemas.QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Question).get(question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    return obj


@router.put("/{question_id}", response_model=schemas.QuestionOut)
def update_question(question_id: int, payload: schemas.QuestionUpdate, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    obj = db.query(models.Question).get(question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Security: Validate and sanitize input
    from ..security_utils import SecurityUtils
    data = payload.dict(exclude_unset=True)
    
    # Sanitize question text if present
    if 'question_text' in data:
        data['question_text'] = SecurityUtils.sanitize_input(data['question_text'])
    
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    obj = db.query(models.Question).get(question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}


