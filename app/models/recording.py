from datetime import datetime
from bson import ObjectId
from app import get_db


class Recording:
    """Recording model for course videos."""
    
    collection_name = 'recordings'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def create(cls, course_id, title: str, drive_file_id: str = None, 
               drive_link: str = None, duration: int = 0, recorded_at: datetime = None):
        """Create a new recording entry."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        recording = {
            'course_id': course_id,
            'title': title,
            'drive_file_id': drive_file_id,
            'drive_link': drive_link,
            'duration': duration,
            'recorded_at': recorded_at or datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        result = cls.get_collection().insert_one(recording)
        recording['_id'] = result.inserted_id
        return recording
    
    @classmethod
    def find_by_id(cls, recording_id):
        """Find recording by ID."""
        if isinstance(recording_id, str):
            recording_id = ObjectId(recording_id)
        return cls.get_collection().find_one({'_id': recording_id})
    
    @classmethod
    def find_by_course(cls, course_id):
        """Get all recordings for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return list(cls.get_collection().find({'course_id': course_id}).sort('recorded_at', 1))
    
    @classmethod
    def update(cls, recording_id, data: dict):
        """Update recording."""
        if isinstance(recording_id, str):
            recording_id = ObjectId(recording_id)
        return cls.get_collection().update_one({'_id': recording_id}, {'$set': data})
    
    @classmethod
    def count_by_course(cls, course_id) -> int:
        """Count recordings for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().count_documents({'course_id': course_id})
    
    @classmethod
    def delete(cls, recording_id):
        """Delete a recording."""
        if isinstance(recording_id, str):
            recording_id = ObjectId(recording_id)
        return cls.get_collection().delete_one({'_id': recording_id})
    
    @classmethod
    def delete_by_course(cls, course_id):
        """Delete all recordings for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().delete_many({'course_id': course_id})
