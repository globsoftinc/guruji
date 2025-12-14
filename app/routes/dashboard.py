from flask import Blueprint, render_template, request, redirect, url_for, g
from datetime import datetime, timezone
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.recording import Recording
from app.utils.validators import validate_clerk_user_id

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def dashboard():
    """Dashboard page - auth handled client-side by Clerk."""
    return render_template('dashboard/main.html')


@dashboard_bp.route('/dashboard/instructor')
def instructor_dashboard():
    """Instructor dashboard - data loaded via API."""
    return render_template('dashboard/instructor.html')


@dashboard_bp.route('/dashboard/student')
def student_dashboard():
    """Student dashboard - data loaded via API."""
    return render_template('dashboard/student.html')


@dashboard_bp.route('/select-role')
def select_role():
    """Page for new users to select their role."""
    return render_template('select_role.html')


# API endpoint for role verification
@dashboard_bp.route('/api/verify-role')
def verify_role():
    """Verify user role for access control."""
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return {'error': 'Not authenticated'}, 401
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return {'error': 'User not found'}, 404
    
    return {
        'role': user.get('role', 'student'), 
        'verification_status': user.get('verification_status'),
        'authenticated': True
    }


# API endpoints for dashboard data (these require auth)
@dashboard_bp.route('/api/dashboard/instructor-data')
def instructor_data():
    """Get instructor dashboard data."""
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return {'error': 'Not authenticated'}, 401
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return {'error': 'User not found'}, 404
    
    # Verify instructor role
    if user.get('role') != 'instructor':
        return {'error': 'Instructor access required'}, 403
    
    courses = Course.find_by_instructor(user['_id'])
    
    total_students = 0
    total_recordings = 0
    upcoming_classes = []
    
    # Always use UTC for consistent comparison
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    courses_data = []
    for course in courses:
        student_count = Enrollment.count_by_course(course['_id'])
        recording_count = Recording.count_by_course(course['_id'])
        total_students += student_count
        total_recordings += recording_count
        
        courses_data.append({
            '_id': str(course['_id']),
            'title': course['title'],
            'is_published': course.get('is_published', False),
            'is_completed': course.get('is_completed', False),
            'attendance_active': course.get('attendance_active', False),
            'student_count': student_count,
            'recording_count': recording_count
        })
        
        for scheduled in course.get('scheduled_classes', []):
            scheduled_dt = scheduled.get('datetime')
            # Only include future classes that are NOT manually marked completed
            if scheduled_dt and not scheduled.get('is_completed'):
                if scheduled_dt.tzinfo is None:
                    scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                if scheduled_dt > now_utc:
                    upcoming_classes.append({
                        'title': scheduled.get('title'),
                        'course_title': course['title'],
                        'course_id': str(course['_id']),
                        'event_id': scheduled.get('calendar_event_id'),
                        'datetime': scheduled_dt.isoformat(),
                        'meet_link': scheduled.get('meet_link')
                    })
    
    return {
        'user': {'name': user['name'], 'role': user['role']},
        'stats': {
            'total_courses': len(courses),
            'total_students': total_students,
            'total_recordings': total_recordings,
            'upcoming_classes': len(upcoming_classes)
        },
        'courses': courses_data,
        'upcoming_classes': upcoming_classes[:5],
        'has_google': bool(user.get('google_tokens')),
        'google_email': user.get('google_tokens', {}).get('google_email', '') if user.get('google_tokens') else ''
    }


@dashboard_bp.route('/api/dashboard/student-data')
def student_data():
    """Get student dashboard data."""
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return {'error': 'Not authenticated'}, 401
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return {'error': 'User not found'}, 404
    
    enrollments = Enrollment.find_by_student(user['_id'])
    
    enrolled_courses = []
    upcoming_classes = []
    
    # Always use UTC for consistent comparison
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    for enrollment in enrollments:
        course = Course.find_by_id(enrollment['course_id'])
        if course:
            instructor = User.find_by_id(course['instructor_id'])
            recording_count = Recording.count_by_course(course['_id'])
            recordings = Recording.find_by_course(course['_id'])
            watched = sum(1 for r in recordings if enrollment.get('progress', {}).get(str(r['_id'])))
            progress_percent = int((watched / len(recordings) * 100) if recordings else 0)
            
            # Count completed classes (past scheduled classes or manually marked) - use UTC
            completed_classes_count = 0
            for scheduled in course.get('scheduled_classes', []):
                scheduled_dt = scheduled.get('datetime')
                if scheduled_dt:
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                    if scheduled.get('is_completed') or scheduled_dt <= now_utc:
                        completed_classes_count += 1
            
            enrolled_courses.append({
                '_id': str(course['_id']),
                'title': course['title'],
                'instructor_name': instructor['name'] if instructor else 'Instructor',
                'recording_count': recording_count,
                'completed_classes_count': completed_classes_count,
                'progress_percent': progress_percent,
                'thumbnail': course.get('thumbnail'),
                'is_completed': course.get('is_completed', False)
            })
            
            for scheduled in course.get('scheduled_classes', []):
                scheduled_dt = scheduled.get('datetime')
                # Only include future classes that aren't manually marked completed - use UTC
                if scheduled_dt:
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                    if scheduled_dt > now_utc and not scheduled.get('is_completed'):
                        upcoming_classes.append({
                            'title': scheduled.get('title'),
                            'course_title': course['title'],
                            'datetime': scheduled_dt.isoformat(),
                            'meet_link': scheduled.get('meet_link')
                        })
    
    # Get ALL non-enrolled published courses for recommendations
    all_courses = Course.find_all_published()
    enrolled_ids = [str(e['course_id']) for e in enrollments]
    recommended = []
    for c in all_courses:
        if str(c['_id']) not in enrolled_ids:
            instructor = User.find_by_id(c['instructor_id'])
            recommended.append({
                '_id': str(c['_id']),
                'title': c['title'],
                'price': c.get('price', 0),
                'instructor_name': instructor['name'] if instructor else 'Instructor',
                'thumbnail': c.get('thumbnail')
            })
    
    return {
        'user': {
            'name': user['name'], 
            'role': user['role'],
            'verification_status': user.get('verification_status')
        },
        'enrolled_courses': enrolled_courses,
        'upcoming_classes': upcoming_classes[:5],
        'recommended_courses': recommended,
        'total_recommended': len(recommended)
    }
