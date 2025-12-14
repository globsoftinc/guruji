"""Input validation utilities for security."""
import re
import html
from urllib.parse import urlparse


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Sanitize a string input by escaping HTML and limiting length."""
    if not value:
        return ''
    
    # Convert to string if needed
    value = str(value)
    
    # Escape HTML entities
    value = html.escape(value)
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str, allowed_schemes: list = None) -> bool:
    """Validate URL format and optionally restrict schemes."""
    if not url:
        return False
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urlparse(url)
        return parsed.scheme in allowed_schemes and bool(parsed.netloc)
    except Exception:
        return False


def validate_google_drive_link(url: str) -> bool:
    """Validate that a URL is a valid Google Drive link."""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ['http', 'https'] and
            'drive.google.com' in parsed.netloc
        )
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing dangerous characters."""
    if not filename:
        return ''
    
    # Remove path separators and null bytes
    filename = filename.replace('/', '').replace('\\', '').replace('\x00', '')
    
    # Remove other dangerous characters
    dangerous_chars = ['..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '')
    
    return filename.strip()


def validate_object_id(obj_id: str) -> bool:
    """Validate MongoDB ObjectId format."""
    if not obj_id:
        return False
    
    # ObjectId is a 24-character hex string
    return bool(re.match(r'^[a-fA-F0-9]{24}$', obj_id))


def validate_price(price) -> float:
    """Validate and sanitize price input."""
    try:
        price = float(price)
        # Price should be non-negative and reasonable
        if price < 0:
            return 0.0
        if price > 1000000:  # Max 1 million
            return 1000000.0
        return round(price, 2)
    except (ValueError, TypeError):
        return 0.0


def validate_clerk_user_id(user_id: str) -> bool:
    """Validate Clerk user ID format."""
    if not user_id:
        return False
    
    # Clerk user IDs typically start with 'user_' and have alphanumeric characters
    return bool(re.match(r'^user_[a-zA-Z0-9]+$', user_id))
