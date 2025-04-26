from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import re
from sqlalchemy.exc import IntegrityError
import secrets
from .db_utils import (
    get_user_by_email, get_user_by_id, get_user_by_username,
    create_user, update_user_profile, create_password_reset_token,
    verify_password_reset_token, create_email_verification_token,
    verify_email_token, save_to_db, update_db
)


auth = Blueprint('auth',__name__)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$')


@auth.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        # If user hasn't completed the survey, redirect to survey page
        if not current_user.is_survey_completed:
            return redirect(url_for('views.cs_interest_survey'))
        return redirect(url_for('views.dashboard'))
    
    # Get the from_signup parameter to determine if user came from signup
    from_signup = request.args.get('from_signup', 'false') == 'true'
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=remember)
                user.last_login = datetime.now()
                db.session.commit()
                flash('Logged in successfully!', category='success')
                
                # Check if user has completed the survey
                if not user.is_survey_completed:
                    return redirect(url_for('views.cs_interest_survey'))
                return redirect(url_for('views.dashboard'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')
            
    return render_template('login.html', user=current_user, from_signup=from_signup)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', category='success')
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        # Validation checks
        user = User.query.filter_by(email=email).first()
        
        if user:
            flash('Email already exists.', category='error')
        elif not EMAIL_REGEX.match(email):
            flash('Invalid email format.', category='error')
        elif len(first_name) < 2:
            flash('First name must be at least 2 characters.', category='error')
        elif len(last_name) < 2:
            flash('Last name must be at least 2 characters.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif not PASSWORD_REGEX.match(password1):
            flash('Password must contain at least 8 characters, including uppercase, lowercase, and numbers.', category='error')
        else:
            # Create new user
            try:
                new_user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=generate_password_hash(password1, method='pbkdf2:sha256'),
                    is_active=True,
                    created_at=datetime.now()
                )
                db.session.add(new_user)
                db.session.commit()
                # Store signup message in session instead of flash
                session['signup_success'] = True
                # Pass parameter to login route to indicate coming from signup
                return redirect(url_for('auth.login', from_signup='true'))
            except IntegrityError:
                db.session.rollback()
                flash('An error occurred. Please try again.', category='error')
                return render_template('signup.html')
            
    return render_template('signup.html', user=current_user)



@auth.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if user:
        user.is_verified = True
        user.email_verification_token = None
        db.session.commit()
        flash('Email verified successfully!', category='success')
    else:
        flash('Invalid or expired verification link.', category='error')
    
    return redirect(url_for('auth.login'))



@auth.route('/api/check-username', methods=['POST'])
def api_check_username():
    """API endpoint to check if a username is available"""
    data = request.get_json()
    username = data.get('username', '')
    
    if not username or len(username) < 3:
        return jsonify({'valid': False, 'message': 'Username must be at least 3 characters'})
        
    user = get_user_by_username(username)
    if user:
        return jsonify({'valid': False, 'message': 'Username already taken'})
    
    return jsonify({'valid': True})

@auth.route('/api/check-email', methods=['POST'])
def api_check_email():
    """API endpoint to check if an email is already registered"""
    data = request.get_json()
    email = data.get('email', '')
    
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({'valid': False, 'message': 'Invalid email format'})
        
    user = get_user_by_email(email)
    if user:
        return jsonify({'valid': False, 'message': 'Email already registered'})
    
    return jsonify({'valid': True})






@auth.route('/account/deactivate', methods=['POST'])
@login_required
def deactivate_account():
    """Allows users to deactivate their account"""
    password = request.form.get('password')
    
    if not password:
        flash('Please enter your password to confirm account deactivation.', category='error')
        return redirect(url_for('views.settings'))
        
    if not check_password_hash(current_user.password, password):
        flash('Incorrect password. Account deactivation cancelled.', category='error')
        return redirect(url_for('views.settings'))
        
    # Deactivate account
    current_user.is_active = False
    update_db()
    
    # Log out user
    logout_user()
    
    flash('Your account has been deactivated. We hope to see you again soon!', category='success')
    return redirect(url_for('views.home'))

