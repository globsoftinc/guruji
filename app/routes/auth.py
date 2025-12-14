import os
import json
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from svix.webhooks import Webhook, WebhookVerificationError
from app.config import Config
from app.models.user import User
from app.utils.validators import validate_clerk_user_id, sanitize_string, validate_email

# Only allow OAuth over HTTP in development (controlled by environment)
if os.getenv('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Relax scope validation as Google often adds openid/userinfo
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/clerk/webhook', methods=['POST'])
def clerk_webhook():
    """Handle Clerk webhook events for user sync."""
    payload = request.get_data()
    headers = dict(request.headers)
    
    # Verify webhook signature
    if Config.CLERK_WEBHOOK_SECRET:
        try:
            wh = Webhook(Config.CLERK_WEBHOOK_SECRET)
            msg = wh.verify(payload, headers)
        except WebhookVerificationError:
            return jsonify({'error': 'Invalid signature'}), 401
    else:
        msg = json.loads(payload)
    
    event_type = msg.get('type')
    data = msg.get('data', {})
    
    if event_type == 'user.created':
        # Create user in our database
        User.create(
            clerk_id=data.get('id'),
            email=data.get('email_addresses', [{}])[0].get('email_address', ''),
            name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            role='student'  # Default role
        )
    
    elif event_type == 'user.updated':
        # Update user in our database
        User.update(
            clerk_id=data.get('id'),
            data={
                'email': data.get('email_addresses', [{}])[0].get('email_address', ''),
                'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            }
        )
    
    elif event_type == 'user.deleted':
        # Delete user from our database
        User.delete(clerk_id=data.get('id'))
    
    return jsonify({'received': True})


@auth_bp.route('/google')
def google_auth():
    """Start Google OAuth flow."""
    # Store Clerk user ID in session (passed as query param from frontend)
    clerk_user_id = request.args.get('clerk_user_id')
    if clerk_user_id:
        # Validate clerk_user_id format
        if not validate_clerk_user_id(clerk_user_id):
            return jsonify({'error': 'Invalid user ID format'}), 400
        session['pending_clerk_user_id'] = clerk_user_id
    
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': Config.GOOGLE_CLIENT_ID,
                'client_secret': Config.GOOGLE_CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [Config.GOOGLE_REDIRECT_URI]
            }
        },
        scopes=Config.GOOGLE_SCOPES
    )
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['google_oauth_state'] = state
    return redirect(authorization_url)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': Config.GOOGLE_CLIENT_ID,
                'client_secret': Config.GOOGLE_CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [Config.GOOGLE_REDIRECT_URI]
            }
        },
        scopes=Config.GOOGLE_SCOPES,
        state=session.get('google_oauth_state')
    )
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    
    # Fix for http/https mismatch behind proxies (e.g. Vercel)
    authorization_response = request.url
    if authorization_response.startswith('http://') and 'https' in Config.GOOGLE_REDIRECT_URI:
        authorization_response = authorization_response.replace('http://', 'https://', 1)
    
    try:
        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    credentials = flow.credentials
    
    # Fetch the Google user's email to show which account is connected
    from googleapiclient.discovery import build
    oauth2_service = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth2_service.userinfo().get().execute()
    google_email = user_info.get('email', '')
    
    tokens = {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
        'google_email': google_email  # Store connected Google email
    }
    
    # Get Clerk user ID from session (saved before redirect)
    clerk_user_id = session.pop('pending_clerk_user_id', None)
    if clerk_user_id:
        User.update_google_tokens(clerk_user_id, tokens)
    
    # Also store in session for immediate use
    session['google_tokens'] = tokens
    
    return redirect('/dashboard/instructor')


@auth_bp.route('/set-role', methods=['POST'])
def set_role():
    """Set user role (for initial setup). Creates user if not exists."""
    data = request.get_json()
    clerk_user_id = data.get('clerk_user_id')
    role = data.get('role')
    email = data.get('email', '')
    name = data.get('name', 'User')
    profile_image = data.get('profile_image')
    
    # Validate inputs
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return jsonify({'error': 'Invalid user ID'}), 400
    if role not in ['instructor', 'student']:
        return jsonify({'error': 'Invalid role'}), 400
    if email and not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Sanitize string inputs
    name = sanitize_string(name, max_length=100) or 'User'
    if profile_image:
        # Simple URL validation for profile image
        if not profile_image.startswith(('https://', 'http://')):
            profile_image = None
    
    # Check if user exists
    user = User.find_by_clerk_id(clerk_user_id)
    
    # Determine verification status for instructors
    verification_status = None
    if role == 'instructor':
        verification_status = 'pending'  # Instructors need approval
    
    if user:
        # Update existing user's role and profile info if missing
        update_data = {'role': role}
        if role == 'instructor':
            # Only set to pending if not already approved
            if user.get('verification_status') != 'approved':
                update_data['verification_status'] = 'pending'
            else:
                verification_status = 'approved'  # Keep approved status
        if email and not user.get('email'):
            update_data['email'] = email
        if name and name != 'User' and user.get('name') == 'User':
            update_data['name'] = name
        if profile_image and not user.get('profile_image'):
            update_data['profile_image'] = profile_image
        User.update(clerk_user_id, update_data)
        verification_status = update_data.get('verification_status', user.get('verification_status'))
    else:
        # Create new user with role
        User.create(
            clerk_id=clerk_user_id,
            email=email,
            name=name,
            role=role,
            profile_image=profile_image,
            verification_status=verification_status
        )
    
    return jsonify({'success': True, 'role': role, 'verification_status': verification_status})


@auth_bp.route('/sync-profile', methods=['POST'])
def sync_profile():
    """Sync user profile data from Clerk. Updates name, email, profile_image."""
    data = request.get_json()
    clerk_user_id = data.get('clerk_user_id')
    email = data.get('email')
    name = data.get('name')
    profile_image = data.get('profile_image')
    
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return jsonify({'error': 'Invalid user ID'}), 400
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update profile data with validation
    update_data = {}
    if email and validate_email(email):
        update_data['email'] = email
    if name and name != 'User':
        update_data['name'] = sanitize_string(name, max_length=100)
    if profile_image and profile_image.startswith(('https://', 'http://')):
        update_data['profile_image'] = profile_image
    
    if update_data:
        User.update(clerk_user_id, update_data)
    
    return jsonify({'success': True, 'updated': list(update_data.keys())})


@auth_bp.route('/check-verification', methods=['GET'])
def check_verification():
    """Check instructor verification status."""
    clerk_user_id = request.headers.get('X-Clerk-User-Id')
    if not clerk_user_id or not validate_clerk_user_id(clerk_user_id):
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.find_by_clerk_id(clerk_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'role': user.get('role'),
        'verification_status': user.get('verification_status')
    })
