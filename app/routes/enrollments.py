from flask import Blueprint, request, jsonify, g
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.user import User
from app.utils.clerk import require_auth
from app.utils.validators import validate_object_id, validate_clerk_user_id

enrollments_bp = Blueprint('enrollments', __name__)


@enrollments_bp.route('/enrollment-status/<course_id>')
def enrollment_status(course_id):
    """Check if current user is enrolled in a course."""
    # Validate course_id format
    if not validate_object_id(course_id):
        return jsonify({'is_enrolled': False})
    
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return jsonify({'is_enrolled': False})
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return jsonify({'is_enrolled': False})
    
    is_enrolled = Enrollment.is_enrolled(user['_id'], course_id)
    return jsonify({'is_enrolled': is_enrolled})


@enrollments_bp.route('/enroll/<course_id>', methods=['POST'])
@require_auth
def enroll(course_id):
    """Enroll current user in a course."""
    # Validate course_id format
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if not course.get('is_published'):
        return jsonify({'error': 'Course is not available'}), 400
    
    # Check if already enrolled
    if Enrollment.is_enrolled(g.current_user['_id'], course_id):
        return jsonify({'error': 'Already enrolled in this course'}), 400
    
    # Create enrollment
    enrollment = Enrollment.create(
        student_id=g.current_user['_id'],
        course_id=course_id
    )
    
    enrollment['_id'] = str(enrollment['_id'])
    enrollment['student_id'] = str(enrollment['student_id'])
    enrollment['course_id'] = str(enrollment['course_id'])
    
    return jsonify(enrollment), 201


@enrollments_bp.route('/unenroll/<course_id>', methods=['DELETE'])
@require_auth
def unenroll(course_id):
    """Unenroll current user from a course."""
    # Validate course_id format
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    Enrollment.delete(g.current_user['_id'], course_id)
    return jsonify({'success': True})


@enrollments_bp.route('/my-courses')
@require_auth
def my_courses():
    """Get current user's enrolled courses."""
    enrollments = Enrollment.find_by_student(g.current_user['_id'])
    
    courses = []
    for enrollment in enrollments:
        course = Course.find_by_id(enrollment['course_id'])
        if course:
            course['_id'] = str(course['_id'])
            course['instructor_id'] = str(course['instructor_id'])
            course['enrollment'] = {
                'enrolled_at': enrollment['enrolled_at'].isoformat(),
                'progress': enrollment.get('progress', {})
            }
            courses.append(course)
    
    return jsonify(courses)


@enrollments_bp.route('/courses/<course_id>/students')
@require_auth
def course_students(course_id):
    """Get enrolled students for a course (instructor only)."""
    # Validate course_id format
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check ownership
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    enrollments = Enrollment.find_by_course(course_id)
    
    students = []
    for enrollment in enrollments:
        student = User.find_by_id(enrollment['student_id'])
        if student:
            students.append({
                'id': str(student['_id']),
                'name': student['name'],
                'email': student['email'],
                'enrolled_at': enrollment['enrolled_at'].isoformat(),
                'progress': enrollment.get('progress', {})
            })
    
    return jsonify(students)


@enrollments_bp.route('/progress/<course_id>/<recording_id>', methods=['POST'])
@require_auth
def update_progress(course_id, recording_id):
    """Mark a recording as watched."""
    # Validate IDs
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    if not validate_object_id(recording_id):
        return jsonify({'error': 'Invalid recording ID format'}), 400
    
    data = request.get_json() or {}
    watched = data.get('watched', True)
    
    Enrollment.update_progress(
        student_id=g.current_user['_id'],
        course_id=course_id,
        recording_id=recording_id,
        watched=watched
    )
    
    return jsonify({'success': True})
