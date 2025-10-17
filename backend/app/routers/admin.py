from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..security import get_current_user


router = APIRouter()


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Require admin role for admin endpoints"""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/pending", response_model=List[schemas.UserOut])
def list_pending(db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Get all users pending approval"""
    return db.query(models.User).filter(models.User.is_approved == False).all()


@router.get("/users", response_model=List[schemas.UserOut])
def list_all_users(db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Get all users with their approval status"""
    return db.query(models.User).all()


@router.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Get specific user details"""
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/approve/{user_id}", response_model=schemas.UserOut)
def approve_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Approve a user account"""
    print(f"🔄 Approve endpoint called for user_id: {user_id}")
    user = db.query(models.User).get(user_id)
    if not user:
        print(f"❌ User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_approved:
        print(f"⚠️ User already approved: {user.email}")
        raise HTTPException(status_code=400, detail="User is already approved")
    
    print(f"📋 Approving user: {user.email} (current status: {user.is_approved})")
    user.is_approved = True
    db.commit()
    db.refresh(user)
    print(f"✅ User approved successfully: {user.email} (new status: {user.is_approved})")
    return user


@router.post("/reject/{user_id}")
def reject_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Reject a user account (delete permanently)"""
    print(f"🔄 Reject endpoint called for user_id: {user_id}")
    user = db.query(models.User).get(user_id)
    if not user:
        print(f"❌ User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from rejecting themselves
    if user.id == admin_user.id:
        print(f"❌ Admin cannot reject themselves: {user.email}")
        raise HTTPException(status_code=400, detail="Cannot reject your own account")
    
    print(f"📋 Rejecting user: {user.email} (current status: {user.is_approved})")
    
    # Delete the user permanently
    db.delete(user)
    db.commit()
    
    print(f"✅ User rejected and deleted successfully: {user.email}")
    return {"message": "User rejected and deleted successfully", "deleted_user_id": user_id}


@router.post("/revoke/{user_id}", response_model=schemas.UserOut)
def revoke_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Revoke a user's access (set to not approved but keep account)"""
    print(f"🔄 Revoke endpoint called for user_id: {user_id}")
    user = db.query(models.User).get(user_id)
    if not user:
        print(f"❌ User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from revoking themselves
    if user.id == admin_user.id:
        print(f"❌ Admin cannot revoke themselves: {user.email}")
        raise HTTPException(status_code=400, detail="Cannot revoke your own account")
    
    print(f"📋 Revoking user: {user.email} (current status: {user.is_approved})")
    
    # Set user as not approved
    user.is_approved = False
    db.commit()
    db.refresh(user)
    
    print(f"✅ User access revoked successfully: {user.email} (new status: {user.is_approved})")
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Delete a user account permanently"""
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), admin_user: models.User = Depends(require_admin)):
    """Get user statistics for admin dashboard"""
    total_users = db.query(models.User).count()
    pending_users = db.query(models.User).filter(models.User.is_approved == False).count()
    approved_users = db.query(models.User).filter(models.User.is_approved == True).count()
    
    # Count by role
    role_counts = {}
    for role in ["Admin", "Interviewer", "Candidate"]:
        count = db.query(models.User).filter(models.User.role == role).count()
        role_counts[role] = count
    
    return {
        "total_users": total_users,
        "pending_approval": pending_users,
        "approved_users": approved_users,
        "role_distribution": role_counts
    }


