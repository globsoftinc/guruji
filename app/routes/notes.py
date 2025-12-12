from flask import Blueprint, request, jsonify, g
from app.models.note import Note
from app.models.course import Course
from app.utils.clerk import require_auth, require_instructor
from app.utils.validators import sanitize_string, validate_google_drive_link, validate_object_id

notes_bp = Blueprint('notes', __name__)


@notes_bp.route('/api/courses/<course_id>/notes')
@require_auth
def list_notes(course_id):
    """List all notes for a course."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    notes = Note.find_by_course(course_id)
    
    # Convert ObjectIds to strings
    for note in notes:
        note['_id'] = str(note['_id'])
        note['course_id'] = str(note['course_id'])
        if note.get('created_at'):
            note['created_at'] = note['created_at'].isoformat()
    
    return jsonify(notes)


@notes_bp.route('/api/courses/<course_id>/notes', methods=['POST'])
@require_instructor
def add_note(course_id):
    """Add a note to a course."""
    # Validate course_id
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    
    # Validate and sanitize inputs
    title = sanitize_string(data.get('title', ''), max_length=200)
    drive_link = data.get('drive_link', '')
    description = sanitize_string(data.get('description', ''), max_length=1000)
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if not validate_google_drive_link(drive_link):
        return jsonify({'error': 'Invalid Google Drive link'}), 400
    
    note = Note.create(
        course_id=course_id,
        title=title,
        drive_link=drive_link,
        description=description
    )
    
    note['_id'] = str(note['_id'])
    note['course_id'] = str(note['course_id'])
    
    return jsonify(note), 201


@notes_bp.route('/api/courses/<course_id>/notes/<note_id>', methods=['PUT'])
@require_instructor
def update_note(course_id, note_id):
    """Update a note."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    update_data = {}
    
    if 'title' in data:
        update_data['title'] = data['title']
    if 'drive_link' in data:
        update_data['drive_link'] = data['drive_link']
    if 'description' in data:
        update_data['description'] = data['description']
    
    Note.update(note_id, update_data)
    
    return jsonify({'success': True})


@notes_bp.route('/api/courses/<course_id>/notes/<note_id>', methods=['DELETE'])
@require_instructor
def delete_note(course_id, note_id):
    """Delete a note."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    Note.delete(note_id)
    
    return jsonify({'success': True})
