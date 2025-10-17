import os
from typing import List

class Settings:
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-USE-ENV-VAR")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app_data.db")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    
    # File Upload Security
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    ALLOWED_AUDIO_TYPES: List[str] = os.getenv(
        "ALLOWED_AUDIO_TYPES", 
        "audio/webm,audio/wav,audio/mp3,audio/ogg"
    ).split(",")
    
    # Security Headers
    ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

settings = Settings()
