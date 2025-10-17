import os
import uuid
from fastapi import HTTPException, UploadFile
from typing import List
import hashlib
import time
from functools import wraps
from fastapi import Request
import asyncio

class SecurityUtils:
    @staticmethod
    def validate_audio_file(file: UploadFile, max_size_mb: int = 50) -> None:
        """Validate uploaded audio file for security"""
        # Check file size
        if file.size and file.size > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size allowed: {max_size_mb}MB"
            )
        
        # Check file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only audio files are allowed"
            )
        
        # Additional security checks
        allowed_types = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/ogg', 'audio/mpeg']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported audio format. Allowed: {', '.join(allowed_types)}"
            )

    @staticmethod
    def generate_secure_filename(original_filename: str) -> str:
        """Generate a secure filename to prevent path traversal"""
        # Get file extension
        _, ext = os.path.splitext(original_filename)
        
        # Generate secure filename with timestamp and UUID
        timestamp = str(int(time.time()))
        unique_id = str(uuid.uuid4())[:8]
        
        # Sanitize extension
        safe_ext = "".join(c for c in ext if c.isalnum() or c in "._-")
        if not safe_ext.startswith('.'):
            safe_ext = '.' + safe_ext
        
        return f"upload_{timestamp}_{unique_id}{safe_ext}"

    @staticmethod
    def sanitize_input(text: str, max_length: int = 10000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not text:
            return ""
        
        # Limit length
        text = text[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text.strip()

    @staticmethod
    def validate_session_ownership(user_id: int, session_user_id: int) -> None:
        """Validate that user owns the session they're trying to access"""
        if user_id != session_user_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied. You can only access your own sessions."
            )

    @staticmethod
    def check_admin_privileges(user_role: str) -> None:
        """Check if user has admin privileges"""
        if user_role != "Admin":
            raise HTTPException(
                status_code=403, 
                detail="Admin privileges required for this action"
            )

# Rate limiting decorator
def rate_limit(requests_per_minute: int = 60):
    """Simple in-memory rate limiter"""
    request_counts = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                return func(*args, **kwargs)
            
            # Get client IP
            client_ip = request.client.host
            current_time = int(time.time() / 60)  # Current minute
            
            # Clean old entries
            request_counts = {k: v for k, v in request_counts.items() 
                            if k[1] >= current_time - 1}
            
            # Check rate limit
            key = (client_ip, current_time)
            if key in request_counts and request_counts[key] >= requests_per_minute:
                raise HTTPException(
                    status_code=429, 
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Increment counter
            request_counts[key] = request_counts.get(key, 0) + 1
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
