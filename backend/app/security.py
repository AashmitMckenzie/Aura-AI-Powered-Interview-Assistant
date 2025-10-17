from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import os

from jose import jwt, JWTError
from passlib.context import CryptContext
import warnings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .config import settings


# Use environment variable for secret key with fallback
SECRET_KEY = settings.SECRET_KEY
if SECRET_KEY == "CHANGE-THIS-IN-PRODUCTION-USE-ENV-VAR":
    # Generate a random secret key for development
    SECRET_KEY = secrets.token_urlsafe(32)
    print("WARNING: Using auto-generated secret key. Set SECRET_KEY environment variable for production!")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Suppress bcrypt version warnings
warnings.filterwarnings("ignore", message=".*bcrypt.*")

# Use a more compatible bcrypt configuration
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
except Exception as e:
    print(f"Warning: Could not initialize bcrypt with rounds=12, falling back to default: {e}")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Ensure password is not too long for bcrypt
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        
        # Try bcrypt first
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as bcrypt_error:
            print(f"Bcrypt verification failed: {bcrypt_error}")
            
            # If bcrypt fails, try SHA256 fallback
            import hashlib
            sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
            return sha256_hash == hashed_password
            
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    try:
        # Ensure password is not too long for bcrypt
        if len(password) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Password hashing error: {e}")
        # Fallback to a simple hash if bcrypt fails
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


