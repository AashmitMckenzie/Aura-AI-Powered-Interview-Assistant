from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from fastapi.security import OAuth2PasswordBearer

from ..database import get_db
from .. import models, schemas
from ..security import get_current_user


router = APIRouter()


@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return current_user


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Require admin role for user management"""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    return db.query(models.User).all()


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


