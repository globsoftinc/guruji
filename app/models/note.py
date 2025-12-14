from datetime import datetime
from bson import ObjectId
from app import get_db


class Note:
    """Note model for course materials (PDFs, documents)."""
    
    collection_name = 'notes'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def create(cls, course_id: str, title: str, drive_link: str, description: str = None):
        """Create a new note."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        note = {
            'course_id': course_id,
            'title': title,
            'drive_link': drive_link,
            'description': description,
            'created_at': datetime.utcnow()
        }
        result = cls.get_collection().insert_one(note)
        note['_id'] = result.inserted_id
        return note
    
    @classmethod
    def find_by_course(cls, course_id):
        """Find all notes for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return list(cls.get_collection().find({'course_id': course_id}).sort('created_at', -1))
    
    @classmethod
    def find_by_id(cls, note_id):
        """Find note by ID."""
        if isinstance(note_id, str):
            note_id = ObjectId(note_id)
        return cls.get_collection().find_one({'_id': note_id})
    
    @classmethod
    def update(cls, note_id, data: dict):
        """Update note data."""
        if isinstance(note_id, str):
            note_id = ObjectId(note_id)
        return cls.get_collection().update_one(
            {'_id': note_id},
            {'$set': data}
        )
    
    @classmethod
    def delete(cls, note_id):
        """Delete a note."""
        if isinstance(note_id, str):
            note_id = ObjectId(note_id)
        return cls.get_collection().delete_one({'_id': note_id})
    
    @classmethod
    def delete_by_course(cls, course_id):
        """Delete all notes for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().delete_many({'course_id': course_id})
    
    @classmethod
    def count_by_course(cls, course_id):
        """Count notes for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().count_documents({'course_id': course_id})
