from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import Base, engine, get_db
from .seed_questions import seed_questions
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from .routers import auth, admin, users, questions, ai, sessions, reports, sentiment, continuous_ai, realtime_bias, question_selector, unified_analysis
from . import models, schemas
from .security import get_password_hash
from .config import settings
from .error_handlers import SecureErrorHandler
from .security_middleware import SecurityMiddleware, RequestLoggingMiddleware


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Local Interview Assistant API", version="0.1.0")

# Security: Add security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Security: Use environment-based CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security: Add secure error handlers
app.add_exception_handler(HTTPException, SecureErrorHandler.http_exception_handler)
app.add_exception_handler(StarletteHTTPException, SecureErrorHandler.http_exception_handler)
app.add_exception_handler(RequestValidationError, SecureErrorHandler.validation_exception_handler)
app.add_exception_handler(Exception, SecureErrorHandler.general_exception_handler)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
app.include_router(continuous_ai.router, prefix="/continuous", tags=["continuous"])
app.include_router(realtime_bias.router, prefix="/bias-realtime", tags=["realtime-bias"])
app.include_router(question_selector.router, prefix="/question-selector", tags=["question-selector"])
app.include_router(unified_analysis.router, prefix="/unified-analysis", tags=["unified-analysis"])


@app.post("/seed")
def trigger_seed(db: Session = Depends(get_db)):
    added = seed_questions(db)
    return {"seeded": added}


@app.post("/create-admin")
def create_admin(email: str, password: str, db: Session = Depends(get_db)):
    """Create an admin account directly (bypasses approval system)"""
    
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
            is_approved=True,  # Bypass approval system
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


