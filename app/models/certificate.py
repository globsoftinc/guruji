from datetime import datetime
from bson import ObjectId
import secrets
import string
from app import get_db


class Certificate:
    """Certificate model for course completion."""
    
    collection_name = 'certificates'
    
    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]
    
    @classmethod
    def generate_code(cls, length=12):
        """Generate a unique certificate verification code."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            # Format as XXXX-XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:12]}"
            # Check if code already exists
            if not cls.get_collection().find_one({'certificate_code': formatted_code}):
                return formatted_code
    
    @classmethod
    def create(cls, student_id, course_id, student_name: str, course_title: str, 
               instructor_name: str, attendance_count: int, total_classes: int,
               attendance_percentage: float):
        """Create a new certificate."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        
        # Check if certificate already exists
        existing = cls.get_collection().find_one({
            'student_id': student_id,
            'course_id': course_id
        })
        if existing:
            return existing
        
        certificate = {
            'student_id': student_id,
            'course_id': course_id,
            'certificate_code': cls.generate_code(),
            'student_name': student_name,
            'course_title': course_title,
            'instructor_name': instructor_name,
            'attendance_count': attendance_count,
            'total_classes': total_classes,
            'attendance_percentage': attendance_percentage,
            'issued_at': datetime.utcnow(),
            'is_valid': True
        }
        result = cls.get_collection().insert_one(certificate)
        certificate['_id'] = result.inserted_id
        return certificate
    
    @classmethod
    def find_by_code(cls, certificate_code: str):
        """Find certificate by verification code."""
        return cls.get_collection().find_one({'certificate_code': certificate_code.upper()})
    
    @classmethod
    def find_by_student(cls, student_id):
        """Get all certificates for a student."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        return list(cls.get_collection().find({'student_id': student_id}))
    
    @classmethod
    def find_by_student_and_course(cls, student_id, course_id):
        """Get certificate for a specific student and course."""
        if isinstance(student_id, str):
            student_id = ObjectId(student_id)
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return cls.get_collection().find_one({
            'student_id': student_id,
            'course_id': course_id
        })
    
    @classmethod
    def invalidate(cls, certificate_id):
        """Invalidate a certificate."""
        if isinstance(certificate_id, str):
            certificate_id = ObjectId(certificate_id)
        return cls.get_collection().update_one(
            {'_id': certificate_id},
            {'$set': {'is_valid': False}}
        )
