import os
import uuid
import base64
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User

auth_bp = Blueprint('auth', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@auth_bp.route('/')
def home():
    """Redirect root access to Candidate Dashboard if logged in, else Login page."""
    if session.get('user_id'):
        return redirect(url_for('exam.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Candidate Registration with identity snapshot capture."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        student_id = request.form.get('student_id', '').strip()
        institution = request.form.get('institution', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()
        cgpa = request.form.get('cgpa', '').strip()
        captured_image_data = request.form.get('captured_image_data', '')

        if not full_name or not email or not password:
            flash('Name, Email, and Password are required.', 'error')
            return render_template('register.html')

        if User.get_by_email(email):
            flash('Email address is already registered. Please log in.', 'error')
            return render_template('register.html')

        photo_filename = None

        # Handle File Upload (photo)
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            ext = os.path.splitext(file.filename)[1] or '.jpg'
            photo_filename = f"upload_{uuid.uuid4().hex[:10]}{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, photo_filename)
            file.save(filepath)
        elif captured_image_data and ',' in captured_image_data:
            try:
                img_str = captured_image_data.split(',')[1]
                img_bytes = base64.b64decode(img_str)
                photo_filename = f"webcam_{uuid.uuid4().hex[:10]}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, photo_filename)
                with open(filepath, 'wb') as f:
                    f.write(img_bytes)
            except Exception as err:
                print(f"Error saving image: {err}")

        reg_no = f"WD-2026-{uuid.uuid4().hex[:6].upper()}"

        try:
            user_id = User.create(
                full_name=full_name,
                email=email,
                password=password,
                photo_path=photo_filename,
                phone=phone,
                dob=dob,
                gender=gender,
                student_id=student_id,
                institution=institution,
                department=department,
                semester=semester,
                cgpa=cgpa,
                registration_no=reg_no
            )

            session['user_id'] = user_id
            session['full_name'] = full_name
            session['email'] = email
            session['photo_path'] = photo_filename

            flash('Registration successful! Identity verified.', 'success')
            return redirect(url_for('exam.dashboard'))
        except Exception as err:
            flash(f'An error occurred during registration: {err}', 'error')
            return render_template('register.html')

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Candidate Authentication Login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        user = User.get_by_email(email)
        if user and User.verify_password(user, password):
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['photo_path'] = user.get('photo_path')

            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('exam.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Candidate Logout."""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
def profile():
    """Candidate Profile View."""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your profile.', 'error')
        return redirect(url_for('auth.login'))

    user = User.get_by_id(user_id)
    return render_template('profile.html', user=user)


@auth_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """Update Candidate Personal, Academic & Contact Details."""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'error')
        return redirect(url_for('auth.login'))

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    dob = request.form.get('dob', '').strip()
    gender = request.form.get('gender', '').strip()
    student_id = request.form.get('student_id', '').strip()
    institution = request.form.get('institution', '').strip()
    department = request.form.get('department', '').strip()
    semester = request.form.get('semester', '').strip()
    cgpa = request.form.get('cgpa', '').strip()

    User.update_profile(
        user_id=user_id,
        full_name=full_name,
        email=email,
        phone=phone,
        dob=dob,
        gender=gender,
        student_id=student_id,
        institution=institution,
        department=department,
        semester=semester,
        cgpa=cgpa
    )

    if full_name:
        session['full_name'] = full_name
    if email:
        session['email'] = email

    flash('Personal & Academic details updated successfully!', 'success')
    referrer = request.referrer
    if referrer and ('/dashboard' in referrer or 'tab=profile' in referrer):
        return redirect(url_for('exam.dashboard', tab='profile'))
    elif referrer:
        return redirect(referrer)
    return redirect(url_for('exam.dashboard'))


@auth_bp.route('/students', endpoint='student_list')
@auth_bp.route('/students', endpoint='list_students')
def student_list():
    """Directory showing registered student login information."""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access student directory.', 'error')
        return redirect(url_for('auth.login'))

    all_students = User.get_all_users()
    return render_template('students.html', students=all_students)
