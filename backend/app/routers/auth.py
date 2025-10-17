from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import schemas, models
from ..database import get_db
from ..security import create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
from ..security_utils import rate_limit


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_approved:
        return None
    return user


@router.post("/signup", response_model=schemas.UserOut)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # All new users require admin approval
    user = models.User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        is_approved=False,  # Require admin approval
        role=payload.role or "Candidate",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
@rate_limit(requests_per_minute=10)  # Security: Limit login attempts
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or not approved")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-json", response_model=schemas.Token)
@rate_limit(requests_per_minute=10)  # Security: Limit login attempts
def login_json(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """JSON-based login endpoint for easier frontend integration"""
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or not approved")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/check-approval/{email}", response_model=schemas.UserApprovalStatus)
def check_approval_status(email: str, db: Session = Depends(get_db)):
    """Check if a user's account is approved (for frontend status checking)"""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"is_approved": False, "message": "User not found"}
    
    if user.is_approved:
        return {"is_approved": True, "message": "Account is approved and ready to use"}
    else:
        return {"is_approved": False, "message": "Account is pending admin approval"}


@router.get("/test-auth")
def test_auth():
    """Test endpoint to verify auth router is working"""
    return {"message": "Auth router is working", "status": "ok"}


@router.post("/create-admin-dev")
def create_admin_dev(request: schemas.AdminCreateRequest, db: Session = Depends(get_db)):
    """Development endpoint to create admin account easily"""
    from ..security import get_password_hash
    
    email = request.email
    password = request.password
    
    # Check if admin already exists
    existing_admin = db.query(models.User).filter(models.User.email == email).first()
    
    if existing_admin:
        # Update existing user to admin
        existing_admin.role = "Admin"
        existing_admin.is_approved = True
        existing_admin.hashed_password = get_password_hash(password)
        db.commit()
        db.refresh(existing_admin)
        return {
            "message": "Admin account updated successfully",
            "user": {
                "id": existing_admin.id,
                "email": existing_admin.email,
                "role": existing_admin.role,
                "is_approved": existing_admin.is_approved
            }
        }
    
    # Create new admin account
    try:
        admin_user = models.User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_approved=True,
            role="Admin"
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        return {
            "message": "Admin account created successfully",
            "user": {
                "id": admin_user.id,
                "email": admin_user.email,
                "role": admin_user.role,
                "is_approved": admin_user.is_approved
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating admin account: {str(e)}")


