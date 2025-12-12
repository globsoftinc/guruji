from datetime import datetime
from bson import ObjectId
from app import get_db


class Course:
    """Course model."""
    
    collection_name = 'courses'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def create(cls, title: str, description: str, instructor_id, thumbnail: str = None, price: float = 0):
        """Create a new course."""
        if isinstance(instructor_id, str):
            instructor_id = ObjectId(instructor_id)
        
        course = {
            'title': title,
            'description': description,
            'instructor_id': instructor_id,
            'thumbnail': thumbnail,
            'price': price,
            'is_published': False,
            'scheduled_classes': [],
            'created_at': datetime.utcnow()
        }
        result = cls.get_collection().insert_one(course)
        course['_id'] = result.inserted_id
        return course
    
    @classmethod
    def find_by_id(cls, course_id):
        """Find course by ID."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().find_one({'_id': course_id})
    
    @classmethod
    def find_all_published(cls):
        """Get all published courses."""
        return list(cls.get_collection().find({'is_published': True}).sort('created_at', -1))
    
    @classmethod
    def find_by_instructor(cls, instructor_id):
        """Get all courses by instructor."""
        if isinstance(instructor_id, str):
            instructor_id = ObjectId(instructor_id)
        return list(cls.get_collection().find({'instructor_id': instructor_id}).sort('created_at', -1))
    
    @classmethod
    def update(cls, course_id, data: dict):
        """Update course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().update_one({'_id': course_id}, {'$set': data})
    
    @classmethod
    def add_scheduled_class(cls, course_id, class_data: dict):
        """Add a scheduled class to course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().update_one(
            {'_id': course_id},
            {'$push': {'scheduled_classes': class_data}}
        )
    
    @classmethod
    def remove_scheduled_class(cls, course_id, event_id: str):
        """Remove a scheduled class."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().update_one(
            {'_id': course_id},
            {'$pull': {'scheduled_classes': {'calendar_event_id': event_id}}}
        )
    
    @classmethod
    def mark_class_completed(cls, course_id, event_id: str):
        """Mark a scheduled class as completed."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().update_one(
            {'_id': course_id, 'scheduled_classes.calendar_event_id': event_id},
            {'$set': {'scheduled_classes.$.is_completed': True}}
        )
    
    @classmethod
    def publish(cls, course_id):
        """Publish a course."""
        return cls.update(course_id, {'is_published': True})
    
    @classmethod
    def unpublish(cls, course_id):
        """Unpublish a course."""
        return cls.update(course_id, {'is_published': False})
    
    @classmethod
    def delete(cls, course_id):
        """Delete a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().delete_one({'_id': course_id})
