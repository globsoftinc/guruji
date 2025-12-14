from flask import Blueprint, render_template, request
from datetime import datetime
from app.models.course import Course
from app.models.user import User
from app.models.enrollment import Enrollment

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def landing():
    """Landing page with course showcase."""
    courses = Course.find_all_published()
    
    # Add instructor info and stats to each course
    for course in courses:
        instructor = User.find_by_id(course['instructor_id'])
        course['instructor'] = instructor
        course['student_count'] = Enrollment.count_by_course(course['_id'])
    
    return render_template('landing.html', courses=courses)


@main_bp.route('/verification-pending')
def verification_pending():
    """Show verification pending page for instructors awaiting approval."""
    return render_template('verification_pending.html')


@main_bp.route('/sign-in')
def sign_in():
    """Sign in page with embedded Clerk component (for in-app browsers)."""
    redirect_url = request.args.get('redirect_url', '/dashboard')
    return render_template('sign-in.html', redirect_url=redirect_url)


@main_bp.route('/sign-up')
def sign_up():
    """Sign up page with embedded Clerk component (for in-app browsers)."""
    redirect_url = request.args.get('redirect_url', '/dashboard')
    return render_template('sign-up.html', redirect_url=redirect_url)


@main_bp.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'ok'}

@main_bp.route("/favicon.ico")
def favicon():
    return "", 200
