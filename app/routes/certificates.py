from flask import Blueprint, request, jsonify, g, render_template, send_file
from datetime import datetime
import re
from app.models.certificate import Certificate
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.user import User
from app.utils.clerk import require_auth, require_instructor
from app.services.certificate_generator import CertificateGenerator
from app.utils.validators import validate_object_id, sanitize_string

certificates_bp = Blueprint('certificates', __name__)


def validate_certificate_code(code):
    """Validate certificate code format."""
    if not code or not isinstance(code, str):
        return False
    # Certificate codes are typically alphanumeric, 8-32 characters
    return bool(re.match(r'^[A-Z0-9-]{8,32}$', code.upper()))


@certificates_bp.route('/api/courses/<course_id>/toggle-attendance', methods=['POST'])
@require_instructor
def toggle_attendance(course_id):
    """Toggle attendance mode for a course (instructor only)."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    current_status = course.get('attendance_active', False)
    new_status = not current_status
    
    # Generate a unique class_id for this attendance session if activating
    update_data = {'attendance_active': new_status}
    if new_status:
        # Create a unique class ID based on timestamp
        class_id = f"class_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        update_data['current_class_id'] = class_id
    else:
        update_data['current_class_id'] = None
    
    Course.update(course_id, update_data)
    
    return jsonify({
        'attendance_active': new_status,
        'class_id': update_data.get('current_class_id')
    })


@certificates_bp.route('/api/courses/<course_id>/attendance-status')
@require_auth
def attendance_status(course_id):
    """Check if attendance is active for a course."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    return jsonify({
        'attendance_active': course.get('attendance_active', False),
        'class_id': course.get('current_class_id')
    })


@certificates_bp.route('/api/courses/<course_id>/mark-attendance', methods=['POST'])
@require_auth
def mark_attendance(course_id):
    """Mark attendance for current user (student)."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if not course.get('attendance_active'):
        return jsonify({'error': 'Attendance is not active'}), 400
    
    # Check if user is enrolled
    if not Enrollment.is_enrolled(g.current_user['_id'], course_id):
        return jsonify({'error': 'Not enrolled in this course'}), 403
    
    class_id = course.get('current_class_id')
    if not class_id:
        return jsonify({'error': 'No active class session'}), 400
    
    # Mark attendance
    marked = Enrollment.mark_attendance(g.current_user['_id'], course_id, class_id)
    
    if marked:
        return jsonify({'success': True, 'message': 'Attendance marked!'})
    else:
        return jsonify({'success': False, 'message': 'Already marked attendance for this class'})


@certificates_bp.route('/api/courses/<course_id>/my-attendance')
@require_auth
def my_attendance(course_id):
    """Get current user's attendance for a course."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    enrollment = Enrollment.find_one(g.current_user['_id'], course_id)
    if not enrollment:
        return jsonify({'error': 'Not enrolled'}), 404
    
    return jsonify({
        'attendance_count': enrollment.get('attendance_count', 0),
        'attendance': enrollment.get('attendance', [])
    })


@certificates_bp.route('/api/courses/<course_id>/generate-certificate', methods=['POST'])
@require_auth
def generate_certificate(course_id):
    """Generate certificate for a completed course."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if course is completed
    if not course.get('is_completed'):
        return jsonify({'error': 'Course is not completed yet'}), 400
    
    # Check if user is enrolled
    enrollment = Enrollment.find_one(g.current_user['_id'], course_id)
    if not enrollment:
        return jsonify({'error': 'Not enrolled in this course'}), 403
    
    # Check if certificate already exists
    existing = Certificate.find_by_student_and_course(g.current_user['_id'], course_id)
    if existing:
        existing['_id'] = str(existing['_id'])
        existing['student_id'] = str(existing['student_id'])
        existing['course_id'] = str(existing['course_id'])
        existing['issued_at'] = existing['issued_at'].isoformat()
        return jsonify(existing)
    
    # Calculate attendance
    attendance_count = enrollment.get('attendance_count', 0)
    
    # Count completed classes - same logic as course detail page
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    total_classes = 0
    for scheduled in course.get('scheduled_classes', []):
        scheduled_dt = scheduled.get('datetime')
        if scheduled_dt:
            # Ensure scheduled_dt is timezone-aware (assume UTC if naive)
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
            # Check if manually marked as completed OR time has passed
            if scheduled.get('is_completed') or scheduled_dt <= now_utc:
                total_classes += 1
    
    if total_classes == 0:
        return jsonify({'error': 'No classes have been completed'}), 400
    
    attendance_percentage = round((attendance_count / total_classes) * 100, 1) if total_classes > 0 else 0
    
    # Get instructor name
    instructor = User.find_by_id(course['instructor_id'])
    instructor_name = instructor['name'] if instructor else 'Instructor'
    
    # Create certificate
    certificate = Certificate.create(
        student_id=g.current_user['_id'],
        course_id=course_id,
        student_name=g.current_user['name'],
        course_title=course['title'],
        instructor_name=instructor_name,
        attendance_count=attendance_count,
        total_classes=total_classes,
        attendance_percentage=attendance_percentage
    )
    
    certificate['_id'] = str(certificate['_id'])
    certificate['student_id'] = str(certificate['student_id'])
    certificate['course_id'] = str(certificate['course_id'])
    certificate['issued_at'] = certificate['issued_at'].isoformat()
    
    return jsonify(certificate), 201


@certificates_bp.route('/api/courses/<course_id>/certificate')
@require_auth
def get_certificate(course_id):
    """Get certificate for current user and course."""
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    certificate = Certificate.find_by_student_and_course(g.current_user['_id'], course_id)
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404
    
    certificate['_id'] = str(certificate['_id'])
    certificate['student_id'] = str(certificate['student_id'])
    certificate['course_id'] = str(certificate['course_id'])
    certificate['issued_at'] = certificate['issued_at'].isoformat()
    
    return jsonify(certificate)


@certificates_bp.route('/api/certificates/verify/<code>')
def verify_certificate(code):
    """Verify a certificate by code (public endpoint)."""
    if not validate_certificate_code(code):
        return jsonify({'valid': False, 'error': 'Invalid certificate code format'}), 400
    
    certificate = Certificate.find_by_code(code)
    if not certificate:
        return jsonify({'valid': False, 'error': 'Certificate not found'}), 404
    
    return jsonify({
        'valid': certificate.get('is_valid', True),
        'certificate_code': certificate['certificate_code'],
        'student_name': certificate['student_name'],
        'course_title': certificate['course_title'],
        'instructor_name': certificate['instructor_name'],
        'attendance_count': certificate['attendance_count'],
        'total_classes': certificate['total_classes'],
        'attendance_percentage': certificate['attendance_percentage'],
        'issued_at': certificate['issued_at'].isoformat()
    })


@certificates_bp.route('/api/my-certificates')
@require_auth
def my_certificates():
    """Get all certificates for current user."""
    certificates = Certificate.find_by_student(g.current_user['_id'])
    
    result = []
    for cert in certificates:
        cert['_id'] = str(cert['_id'])
        cert['student_id'] = str(cert['student_id'])
        cert['course_id'] = str(cert['course_id'])
        cert['issued_at'] = cert['issued_at'].isoformat()
        result.append(cert)
    
    return jsonify(result)


@certificates_bp.route('/api/certificates/<code>/image')
def certificate_image(code):
    """Generate and return certificate as PNG image."""
    if not validate_certificate_code(code):
        return jsonify({'error': 'Invalid certificate code format'}), 400
    
    certificate = Certificate.find_by_code(code)
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404
    
    img_buffer = CertificateGenerator.generate_certificate_image(
        student_name=certificate['student_name'],
        course_title=certificate['course_title'],
        instructor_name=certificate['instructor_name'],
        certificate_code=certificate['certificate_code'],
        attendance_count=certificate['attendance_count'],
        total_classes=certificate['total_classes'],
        attendance_percentage=certificate['attendance_percentage'],
        issued_date=certificate['issued_at']
    )
    
    return send_file(
        img_buffer,
        mimetype='image/png',
        as_attachment=False,
        download_name=f"certificate_{code}.png"
    )


@certificates_bp.route('/api/certificates/<code>/download')
def certificate_download(code):
    """Generate and download certificate as PDF."""
    if not validate_certificate_code(code):
        return jsonify({'error': 'Invalid certificate code format'}), 400
    
    certificate = Certificate.find_by_code(code)
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404
    
    pdf_buffer = CertificateGenerator.generate_certificate_pdf(
        student_name=certificate['student_name'],
        course_title=certificate['course_title'],
        instructor_name=certificate['instructor_name'],
        certificate_code=certificate['certificate_code'],
        attendance_count=certificate['attendance_count'],
        total_classes=certificate['total_classes'],
        attendance_percentage=certificate['attendance_percentage'],
        issued_date=certificate['issued_at']
    )
    
    # Create a safe filename
    safe_name = certificate['student_name'].replace(' ', '_')
    safe_course = certificate['course_title'].replace(' ', '_')[:30]
    filename = f"Certificate_{safe_name}_{safe_course}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@certificates_bp.route('/verify')
def verify_page():
    """Certificate verification page."""
    return render_template('verify.html')

