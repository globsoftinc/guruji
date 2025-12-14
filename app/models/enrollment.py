from datetime import datetime
from bson import ObjectId
from app import get_db


class Enrollment:
    """Student enrollment model."""
    
    collection_name = 'enrollments'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def create(cls, student_id, course_id):
        """Enroll a student in a course."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        # Check if already enrolled
        existing = cls.get_collection().find_one({
            'student_id': student_id,
            'course_id': course_id
        })
        if existing:
            return existing
        
        enrollment = {
            'student_id': student_id,
            'course_id': course_id,
            'enrolled_at': datetime.utcnow(),
            'progress': {},
            'attendance': [],  # List of class IDs attended
            'attendance_count': 0
        }
        result = cls.get_collection().insert_one(enrollment)
        enrollment['_id'] = result.inserted_id
        return enrollment
    
    @classmethod
    def find_by_student(cls, student_id):
        """Get all enrollments for a student."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        return list(cls.get_collection().find({'student_id': student_id}))
    
    @classmethod
    def find_by_course(cls, course_id):
        """Get all enrollments for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return list(cls.get_collection().find({'course_id': course_id}))
    
    @classmethod
    def find_one(cls, student_id, course_id):
        """Get a specific enrollment."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().find_one({
            'student_id': student_id,
            'course_id': course_id
        })
    
    @classmethod
    def is_enrolled(cls, student_id, course_id) -> bool:
        """Check if student is enrolled in course."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().find_one({
            'student_id': student_id,
            'course_id': course_id
        }) is not None
    
    @classmethod
    def update_progress(cls, student_id, course_id, recording_id: str, watched: bool = True):
        """Update watch progress for a recording."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        return cls.get_collection().update_one(
            {'student_id': student_id, 'course_id': course_id},
            {'$set': {f'progress.{recording_id}': watched}}
        )
    
    @classmethod
    def mark_attendance(cls, student_id, course_id, class_id: str):
        """Mark attendance for a class."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        # Add class_id to attendance array if not already present
        result = cls.get_collection().update_one(
            {
                'student_id': student_id,
                'course_id': course_id,
                'attendance': {'$ne': class_id}
            },
            {
                '$push': {'attendance': class_id},
                '$inc': {'attendance_count': 1}
            }
        )
        return result.modified_count > 0
    
    @classmethod
    def get_attendance_count(cls, student_id, course_id) -> int:
        """Get attendance count for a student in a course."""
        enrollment = cls.find_one(student_id, course_id)
        if enrollment:
            return enrollment.get('attendance_count', 0)
        return 0
    
    @classmethod
    def count_by_course(cls, course_id) -> int:
        """Count enrollments for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().count_documents({'course_id': course_id})
    
    @classmethod
    def delete(cls, student_id, course_id):
        """Remove enrollment."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().delete_one({
            'student_id': student_id,
            'course_id': course_id
        })
    
    @classmethod
    def delete_by_course(cls, course_id):
        """Delete all enrollments for a course."""
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().delete_many({'course_id': course_id})
