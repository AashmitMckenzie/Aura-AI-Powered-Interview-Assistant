from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for additional protections"""
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Security: Add security headers
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Log request for monitoring
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and detecting suspicious activity"""
    
    async def dispatch(self, request: Request, call_next):
        # Log request details
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        
        # Basic suspicious activity detection
        suspicious_patterns = [
            "..",  # Path traversal
            "<script",  # XSS attempts
            "union select",  # SQL injection
            "eval(",  # Code injection
            "base64",  # Potential encoding attacks
        ]
        
        suspicious_detected = any(pattern.lower() in path.lower() or 
                                 pattern.lower() in str(request.query_params).lower() 
                                 for pattern in suspicious_patterns)
        
        if suspicious_detected:
            logger.warning(f"Suspicious activity detected from {client_ip}: {request.method} {path}")
        
        response = await call_next(request)
        
        # Log response
        if response.status_code >= 400:
            logger.warning(f"Error response {response.status_code} for {request.method} {path} from {client_ip}")
        
        return response
