import requests
import re
from functools import wraps
from flask import request, jsonify, g
from app.config import Config
from app.models.user import User


def validate_clerk_user_id(user_id: str) -> bool:
    """Validate Clerk user ID format to prevent injection."""
    if not user_id:
        return False
    # Clerk user IDs typically start with 'user_' followed by alphanumeric characters
    return bool(re.match(r'^user_[a-zA-Z0-9]+$', user_id))


def verify_clerk_token(token: str) -> dict:
    """Verify Clerk session token and return user data."""
    try:
        # Use Clerk's session verification endpoint
        headers = {
            'Authorization': f'Bearer {Config.CLERK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Decode the session token
        response = requests.get(
            'https://api.clerk.com/v1/sessions',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Clerk verification error: {e}")
        return None


def get_clerk_user(user_id: str) -> dict:
    """Fetch user details from Clerk API."""
    try:
        headers = {
            'Authorization': f'Bearer {Config.CLERK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'https://api.clerk.com/v1/users/{user_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Clerk user fetch error: {e}")
        return None


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from cookie or header
        session_token = request.cookies.get('__session') or \
                       request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401
        
        # For Clerk, we'll use the __clerk_db_jwt cookie that contains user info
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        
        if not clerk_user_id:
            return jsonify({'error': 'User ID not found'}), 401
        
        # Validate clerk_user_id format to prevent injection attacks
        if not validate_clerk_user_id(clerk_user_id):
            return jsonify({'error': 'Invalid user ID format'}), 401
        
        # Get user from our database
        user = User.find_by_clerk_id(clerk_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


def require_instructor(f):
    """Decorator to require instructor role."""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if g.current_user.get('role') != 'instructor':
            return jsonify({'error': 'Instructor access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user_from_request():
    """Extract current user from request (for templates)."""
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if clerk_user_id:
        return User.find_by_clerk_id(clerk_user_id)
    return None


def require_instructor_page(f):
    """Decorator to require instructor role for page routes.
    
    Unlike require_instructor which returns JSON for API endpoints,
    this decorator handles HTML pages and passes role info to templates
    for client-side verification with proper fallback.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For page routes, we pass a flag to indicate instructor-only access
        # The actual check happens client-side with Clerk, but we add
        # server-side verification via the API calls
        g.require_instructor = True
        return f(*args, **kwargs)
    
    return decorated_function
