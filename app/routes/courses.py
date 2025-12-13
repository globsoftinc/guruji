from flask import Blueprint, render_template, request, jsonify, g
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from app.models.course import Course
from app.models.recording import Recording
from app.models.enrollment import Enrollment
from app.models.note import Note
from app.models.user import User
from app.utils.clerk import require_auth, require_instructor
from app.utils.validators import sanitize_string, validate_url, validate_price, validate_object_id
from app.services.google_meet import GoogleMeetService

courses_bp = Blueprint('courses', __name__)


@courses_bp.route('/courses')
def list_courses():
    """List all published courses."""
    courses = Course.find_all_published()
    
    # Add instructor info and stats to each course
    for course in courses:
        instructor = User.find_by_id(course['instructor_id'])
        course['instructor'] = instructor
        course['student_count'] = Enrollment.count_by_course(course['_id'])
        
    # Count manually marked completed classes only
    completed_count = 0
    for scheduled in course.get('scheduled_classes', []):
        if scheduled.get('is_completed'):
            completed_count += 1
    course['completed_classes_count'] = completed_count
    
    return render_template('courses/list.html', courses=courses)


@courses_bp.route('/courses/<course_id>')
def course_detail(course_id):
    """View course details."""
    # Validate course_id format to prevent injection
    if not validate_object_id(course_id):
        return render_template('errors/404.html'), 404
    
    try:
        course = Course.find_by_id(course_id)
    except InvalidId:
        return render_template('errors/404.html'), 404
    
    if not course:
        return render_template('errors/404.html'), 404
    
    instructor = User.find_by_id(course['instructor_id'])
    recordings = Recording.find_by_course(course_id)
    student_count = Enrollment.count_by_course(course_id)
    
    # Separate scheduled classes into upcoming and completed
    # Always use UTC for consistent comparison
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    upcoming_classes = []
    completed_classes = []
    for scheduled in course.get('scheduled_classes', []):
        scheduled_dt = scheduled.get('datetime')
        if scheduled_dt:
            # Ensure scheduled_dt is timezone-aware (assume UTC if naive)
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
            # Check if manually marked as completed OR time has passed
            if scheduled.get('is_completed') or scheduled_dt <= now_utc:
                completed_classes.append(scheduled)
            else:
                upcoming_classes.append(scheduled)
    
    # Store both lists in course object for template
    course['upcoming_classes'] = upcoming_classes
    course['completed_classes'] = completed_classes
    
    # Check if current user is enrolled (if logged in)
    is_enrolled = False
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if clerk_user_id:
        user = User.find_by_clerk_id(clerk_user_id)
        if user:
            is_enrolled = Enrollment.is_enrolled(user['_id'], course_id)
    
    return render_template(
        'courses/detail.html',
        course=course,
        instructor=instructor,
        recordings=recordings,
        student_count=student_count,
        is_enrolled=is_enrolled
    )


@courses_bp.route('/courses/create')
def create_course_page():
    """Show create course form. Auth handled client-side."""
    return render_template('courses/create.html')


@courses_bp.route('/api/courses', methods=['POST'])
@require_instructor
def create_course():
    """Create a new course."""
    data = request.get_json()
    
    # Validate and sanitize inputs
    title = sanitize_string(data.get('title', ''), max_length=200)
    description = sanitize_string(data.get('description', ''), max_length=5000)
    thumbnail = data.get('thumbnail')
    price = validate_price(data.get('price', 0))
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if thumbnail and not validate_url(thumbnail):
        return jsonify({'error': 'Invalid thumbnail URL'}), 400
    
    course = Course.create(
        title=title,
        description=description,
        instructor_id=g.current_user['_id'],
        thumbnail=thumbnail,
        price=price
    )
    
    course['_id'] = str(course['_id'])
    course['instructor_id'] = str(course['instructor_id'])
    
    return jsonify(course), 201


@courses_bp.route('/api/courses/<course_id>', methods=['PUT'])
@require_instructor
def update_course(course_id):
    """Update a course."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check ownership
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    update_data = {}
    
    if 'title' in data:
        update_data['title'] = data['title']
    if 'description' in data:
        update_data['description'] = data['description']
    if 'thumbnail' in data:
        update_data['thumbnail'] = data['thumbnail']
    if 'price' in data:
        update_data['price'] = float(data['price'])
    if 'is_published' in data:
        update_data['is_published'] = data['is_published']
    if 'is_completed' in data:
        update_data['is_completed'] = data['is_completed']
    
    Course.update(course_id, update_data)
    
    return jsonify({'success': True})


@courses_bp.route('/api/courses/<course_id>', methods=['DELETE'])
@require_instructor
def delete_course(course_id):
    """Delete a course."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check ownership
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Delete associated recordings
    Recording.delete_by_course(course_id)
    
    # Delete associated notes
    Note.delete_by_course(course_id)
    
    # Delete associated enrollments
    Enrollment.delete_by_course(course_id)
    
    # Delete course
    Course.delete(course_id)
    
    return jsonify({'success': True})


@courses_bp.route('/api/courses/<course_id>/publish', methods=['POST'])
@require_instructor
def publish_course(course_id):
    """Publish a course."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    Course.publish(course_id)
    return jsonify({'success': True})


@courses_bp.route('/api/courses/<course_id>/schedule-class', methods=['POST'])
@require_instructor
def schedule_class(course_id):
    """Schedule a new class with Google Meet."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Check if user has Google tokens
    if not g.current_user.get('google_tokens'):
        return jsonify({'error': 'Please connect Google account first'}), 400
    
    data = request.get_json()
    
    try:
        meet_service = GoogleMeetService(g.current_user['google_tokens'])
        
        # Parse datetime
        start_time = datetime.fromisoformat(data.get('datetime'))
        
        # Get enrolled student emails (filter out empty/invalid emails)
        enrollments = Enrollment.find_by_course(course_id)
        attendee_emails = []
        for enrollment in enrollments:
            student = User.find_by_id(enrollment['student_id'])
            if student and student.get('email') and '@' in student.get('email', ''):
                attendee_emails.append(student['email'])
        
        # Create Meet event
        result = meet_service.create_meet_event(
            title=f"{course['title']} - {data.get('title', 'Live Class')}",
            start_time=start_time,
            duration_minutes=int(data.get('duration', 60)),
            attendee_emails=attendee_emails
        )
        
        # Add to course
        class_data = {
            'title': data.get('title', 'Live Class'),
            'datetime': start_time,
            'meet_link': result['meet_link'],
            'calendar_event_id': result['event_id']
        }
        
        Course.add_scheduled_class(course_id, class_data)
        
        return jsonify(class_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/api/courses/<course_id>/mark-class-completed', methods=['POST'])
@require_instructor
def mark_class_completed(course_id):
    """Mark a scheduled class as completed manually."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    event_id = data.get('event_id')
    
    if not event_id:
        return jsonify({'error': 'Event ID required'}), 400
    
    # Update the specific class to mark it as completed
    result = Course.mark_class_completed(course_id, event_id)
    
    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Class not found'}), 404


@courses_bp.route('/api/courses/<course_id>/delete-scheduled-class', methods=['POST'])
@require_instructor
def delete_scheduled_class(course_id):
    """Delete a scheduled class."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    event_id = data.get('event_id')
    
    if not event_id:
        return jsonify({'error': 'Event ID required'}), 400
    
    # Remove the scheduled class
    result = Course.remove_scheduled_class(course_id, event_id)
    
    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Class not found'}), 404
