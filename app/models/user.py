from datetime import datetime
from bson import ObjectId
from app import get_db


class User:
    """User model synced from Clerk."""
    
    collection_name = 'users'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def create(cls, clerk_id: str, email: str, name: str, role: str = 'student', profile_image: str = None, verification_status: str = None):
        """Create a new user."""
        user = {
            'clerk_id': clerk_id,
            'email': email,
            'name': name,
            'role': role,  # 'instructor' or 'student'
            'profile_image': profile_image,
            'google_tokens': None,
            'verification_status': verification_status,  # 'pending', 'approved', 'rejected' for instructors
            'created_at': datetime.utcnow()
        }
        result = cls.get_collection().insert_one(user)
        user['_id'] = result.inserted_id
        return user
    
    @classmethod
    def find_by_clerk_id(cls, clerk_id: str):
        """Find user by Clerk ID."""
        return cls.get_collection().find_one({'clerk_id': clerk_id})
    
    @classmethod
    def find_by_id(cls, user_id):
        """Find user by MongoDB ID."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return cls.get_collection().find_one({'_id': user_id})
    
    @classmethod
    def find_by_email(cls, email: str):
        """Find user by email."""
        return cls.get_collection().find_one({'email': email})
    
    @classmethod
    def update(cls, clerk_id: str, data: dict):
        """Update user data."""
        return cls.get_collection().update_one(
            {'clerk_id': clerk_id},
            {'$set': data}
        )
    
    @classmethod
    def update_google_tokens(cls, clerk_id: str, tokens: dict):
        """Update Google OAuth tokens."""
        return cls.update(clerk_id, {'google_tokens': tokens})
    
    @classmethod
    def set_role(cls, clerk_id: str, role: str):
        """Set user role (instructor/student)."""
        return cls.update(clerk_id, {'role': role})
    
    @classmethod
    def delete(cls, clerk_id: str):
        """Delete user."""
        return cls.get_collection().delete_one({'clerk_id': clerk_id})
