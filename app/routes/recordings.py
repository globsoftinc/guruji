from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app.models.recording import Recording
from app.models.course import Course
from app.utils.clerk import require_auth, require_instructor
from app.utils.validators import sanitize_string, validate_google_drive_link, validate_object_id
from app.services.google_drive import GoogleDriveService

recordings_bp = Blueprint('recordings', __name__)


@recordings_bp.route('/courses/<course_id>/recordings')
@require_auth
def list_recordings(course_id):
    """List all recordings for a course."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    recordings = Recording.find_by_course(course_id)
    
    # Convert ObjectIds to strings
    for recording in recordings:
        recording['_id'] = str(recording['_id'])
        recording['course_id'] = str(recording['course_id'])
        if recording.get('recorded_at'):
            recording['recorded_at'] = recording['recorded_at'].isoformat()
        if recording.get('created_at'):
            recording['created_at'] = recording['created_at'].isoformat()
    
    return jsonify(recordings)


@recordings_bp.route('/courses/<course_id>/recordings', methods=['POST'])
@require_instructor
def add_recording(course_id):
    """Manually add a recording to a course."""
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
    drive_file_id = sanitize_string(data.get('drive_file_id', ''), max_length=100)
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if drive_link and not validate_google_drive_link(drive_link):
        return jsonify({'error': 'Invalid Google Drive link'}), 400
    
    # Validate duration
    try:
        duration = max(0, min(int(data.get('duration', 0)), 86400))  # Max 24 hours
    except (ValueError, TypeError):
        duration = 0
    
    # Parse recorded_at safely
    recorded_at = None
    if data.get('recorded_at'):
        try:
            recorded_at = datetime.fromisoformat(data['recorded_at'])
        except ValueError:
            pass
    
    recording = Recording.create(
        course_id=course_id,
        title=title,
        drive_file_id=drive_file_id,
        drive_link=drive_link,
        duration=duration,
        recorded_at=recorded_at
    )
    
    recording['_id'] = str(recording['_id'])
    recording['course_id'] = str(recording['course_id'])
    
    return jsonify(recording), 201


@recordings_bp.route('/courses/<course_id>/recordings/<recording_id>', methods=['PUT'])
@require_instructor
def update_recording(course_id, recording_id):
    """Update a recording."""
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
    if 'duration' in data:
        update_data['duration'] = int(data['duration'])
    
    Recording.update(recording_id, update_data)
    
    return jsonify({'success': True})


@recordings_bp.route('/courses/<course_id>/recordings/<recording_id>', methods=['DELETE'])
@require_instructor
def delete_recording(course_id, recording_id):
    """Delete a recording."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    Recording.delete(recording_id)
    
    return jsonify({'success': True})


@recordings_bp.route('/courses/<course_id>/sync-recordings', methods=['POST'])
@require_instructor
def sync_recordings(course_id):
    """Sync recordings from Google Drive."""
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if course['instructor_id'] != g.current_user['_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Check if user has Google tokens
    if not g.current_user.get('google_tokens'):
        return jsonify({'error': 'Please connect Google account first'}), 400
    
    try:
        drive_service = GoogleDriveService(g.current_user['google_tokens'])
        
        # Get recent Meet recordings
        drive_files = drive_service.list_meet_recordings(days_back=30)
        
        # Get existing recordings to avoid duplicates
        existing = Recording.find_by_course(course_id)
        existing_file_ids = {r.get('drive_file_id') for r in existing if r.get('drive_file_id')}
        
        added = []
        for file in drive_files:
            if file['id'] not in existing_file_ids:
                # Create shareable link
                share_link = drive_service.create_shareable_link(file['id'])
                duration = drive_service.get_video_duration(file['id'])
                
                recording = Recording.create(
                    course_id=course_id,
                    title=file['name'],
                    drive_file_id=file['id'],
                    drive_link=share_link or file.get('webViewLink'),
                    duration=duration,
                    recorded_at=datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00'))
                )
                
                recording['_id'] = str(recording['_id'])
                added.append(recording)
        
        return jsonify({
            'success': True,
            'added_count': len(added),
            'recordings': added
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recordings_bp.route('/drive/recordings')
@require_instructor
def list_drive_recordings():
    """List available recordings from Google Drive."""
    if not g.current_user.get('google_tokens'):
        return jsonify({'error': 'Please connect Google account first'}), 400
    
    try:
        drive_service = GoogleDriveService(g.current_user['google_tokens'])
        recordings = drive_service.list_meet_recordings(days_back=30)
        
        return jsonify(recordings)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
