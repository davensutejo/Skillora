from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from .models import User, PasswordReset, EmailVerification
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

# Email regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Password pattern: minimum 8 characters, at least one uppercase, one lowercase, one number
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$')

@auth.route('/login', methods=['GET','POST'])
def login():
    # Initialize form data with empty values
    form_data = {
        'email': ''
    }
    
    if request.method == 'POST':
        # Get form data and trim whitespace
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        remember = True if request.form.get('remember') else False
        
        print(f"DEBUG: Remember me checked: {remember}")
        
        # Store email to preserve it if validation fails
        form_data = {
            'email': email
        }
        
        # Input validation
        if not email or not password:
            flash('Please fill in all fields.', category='error')
            return render_template('login.html', user=current_user, form_data=form_data)
            
        # Find user by email
        user = get_user_by_email(email)
        
        if user: 
            # Check if account is active
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', category='error')
                return render_template('login.html', user=current_user, form_data=form_data)
                
            # Verify password
            if check_password_hash(user.password, password):
                # Update last login timestamp
                user.last_login = datetime.now()
                update_db()
                
                print("DEBUG: Password verified successfully")
                flash('Logged in successfully!', category='success')
                
                # Log the user in BEFORE redirect
                login_user(user, remember=remember)
                print(f"DEBUG: User logged in: {current_user.is_authenticated}, ID: {current_user.id}")
                
                # Get next page from query parameters
                next_page = request.args.get('next')
                print(f"DEBUG: Next page from args: {next_page}")
                
                if next_page:
                    print(f"DEBUG: Redirecting to next page: {next_page}")
                    return redirect(next_page)
                
                print("DEBUG: No next page, redirecting to dashboard")
                # Use a direct render_template to avoid redirect issues
                return render_template('home.html', user=user)
            else:
                flash('Incorrect password. Please try again.', category='error')
                return render_template('login.html', user=current_user, form_data=form_data)
        else:
            flash('No account found with that email address.', category='error')
            return render_template('login.html', user=current_user, form_data=form_data)

    return render_template('login.html', user=current_user, form_data=form_data)


@auth.route('/logout')
@login_required
def logout():
    # Store username for flash message before logout
    username = current_user.first_name if hasattr(current_user, 'first_name') else 'User'
    
    # Clear the current user session
    logout_user()
    
    # Clear the session completely
    if 'user_id' in session:
        session.pop('user_id')
    if '_user_id' in session:
        session.pop('_user_id')
    if 'remember_token' in session:
        session.pop('remember_token')
    session.clear()
    
    # Create response object
    response = redirect(url_for('views.home'))
    
    # Set cache control headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    # Delete the session cookie and any remember_me cookie
    response.delete_cookie('session')
    response.delete_cookie('remember_token')
    response.delete_cookie('remember_me')
    
    # Also delete all cookies with variations of the domain and path
    domain = request.host.split(':')[0]  # Strip port number if present
    response.delete_cookie('session', domain=domain, path='/')
    response.delete_cookie('remember_token', domain=domain, path='/')
    response.delete_cookie('remember_me', domain=domain, path='/')
    
    # Just to be extra sure, also try localhost variations
    response.delete_cookie('session', domain='localhost', path='/')
    response.delete_cookie('remember_token', domain='localhost', path='/')
    response.delete_cookie('remember_me', domain='localhost', path='/')
    response.delete_cookie('session', domain='127.0.0.1', path='/')
    response.delete_cookie('remember_token', domain='127.0.0.1', path='/')
    response.delete_cookie('remember_me', domain='127.0.0.1', path='/')
    
    flash(f'You have been logged out successfully, {username}.', category='success')
    return response


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    # Initialize form data with empty values
    form_data = {
        'email': '',
        'firstName': '',
        'lastName': ''
    }
    
    if request.method == 'POST':
        # Get form data and trim whitespace
        email = request.form.get('email', '').strip()
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        password1 = request.form.get('password1', '').strip()
        password2 = request.form.get('password2', '').strip()
        
        # Store form data to preserve it in case of validation error
        form_data = {
            'email': email,
            'firstName': first_name,
            'lastName': last_name
        }
        
        # Input validation
        error = None
        
        if not email or not first_name or not password1 or not password2:
            error = 'Please fill in all required fields.'
        elif not EMAIL_REGEX.match(email):
            error = 'Please enter a valid email address.'
        elif get_user_by_email(email):
            error = 'Email already registered. Please use a different email or login.'
        elif len(first_name) < 2:
            error = 'First name must be at least 2 characters.'
        elif password1 != password2:
            error = 'Passwords do not match.'
        elif not PASSWORD_REGEX.match(password1):
            error = 'Password must be at least 8 characters and include uppercase, lowercase, and numbers.'
            
        if error:
            flash(error, category='error')
            return render_template("sign_up.html", user=current_user, form_data=form_data)
        
        try:
            # Create new user
            password_hash = generate_password_hash(password1, method='pbkdf2:sha256')
            new_user = create_user(email, first_name, last_name, password_hash)
            
            if not new_user:
                flash('An error occurred while creating your account. Please try again.', category='error')
                return render_template("sign_up.html", user=current_user, form_data=form_data)
            
            # Mark user as verified directly (skipping email verification for now)
            new_user.is_verified = True
            update_db()
            
            # Log in the new user
            login_user(new_user, remember=True)
            
            flash('Account created successfully!', category='success')
            return redirect(url_for('views.home'))
            
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', category='error')
            return render_template("sign_up.html", user=current_user, form_data=form_data)
                
    return render_template("sign_up.html", user=current_user, form_data=form_data)


@auth.route('/verify-email/<token>')
def verify_email(token):
    """Handles email verification using the token sent to user's email"""
    verification = verify_email_token(token)
    
    if not verification:
        flash('Invalid or expired verification link. Please request a new one.', category='error')
        return redirect(url_for('auth.resend_verification'))
        
    # Mark the user as verified
    user = get_user_by_id(verification.user_id)
    if user:
        user.is_verified = True
        verification.is_used = True
        update_db()
        
        flash('Email verified successfully!', category='success')
        
        # If user is not logged in, redirect to login
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return redirect(url_for('views.home'))
    
    flash('User not found. Please contact support.', category='error')
    return redirect(url_for('auth.login'))


@auth.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Allows users to request a new verification email"""
    # Initialize form data with empty values
    form_data = {
        'email': ''
    }
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # Store email to preserve it if validation fails
        form_data = {
            'email': email
        }
        
        if not email or not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address.', category='error')
            return render_template('resend_verification.html', user=current_user, form_data=form_data)
            
        user = get_user_by_email(email)
        
        if not user:
            # Don't reveal if email exists or not (security best practice)
            flash('If your email is registered, you will receive a verification link shortly.', category='success')
            return redirect(url_for('auth.login'))
            
        if user.is_verified:
            flash('This account is already verified. Please login.', category='info')
            return redirect(url_for('auth.login'))
            
        # Send new verification email
        token = create_email_verification_token(user.id)
        if token:
            send_verification_email_to_user(user, token)
        
        flash('A new verification link has been sent to your email.', category='success')
        return redirect(url_for('auth.login'))
        
    return render_template('resend_verification.html', user=current_user, form_data=form_data)


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handles password reset requests"""
    # Initialize form data with empty values
    form_data = {
        'email': ''
    }
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # Store email to preserve it if validation fails
        form_data = {
            'email': email
        }
        
        if not email or not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address.', category='error')
            return render_template('forgot_password.html', user=current_user, form_data=form_data)
            
        user = get_user_by_email(email)
        
        # Don't reveal if email exists or not
        if user:
            # Generate and store password reset token
            token = create_password_reset_token(user.id)
            if token:
                send_password_reset_email_to_user(user, token)
            
        flash('If your email is registered, you will receive a password reset link shortly.', category='success')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html', user=current_user, form_data=form_data)


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles password reset using the token sent to user's email"""
    reset_request = verify_password_reset_token(token)
    
    if not reset_request:
        flash('Invalid or expired reset link. Please request a new one.', category='error')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password1 = request.form.get('password1', '').strip()
        password2 = request.form.get('password2', '').strip()
        
        if not password1 or not password2:
            flash('Please fill in all fields.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif not PASSWORD_REGEX.match(password1):
            flash('Password must be at least 8 characters and include uppercase, lowercase, and numbers.', category='error')
        else:
            # Update user's password
            user = get_user_by_id(reset_request.user_id)
            if user:
                user.password = generate_password_hash(password1, method='pbkdf2:sha256')
                reset_request.is_used = True
                update_db()
                
                flash('Password updated successfully! You can now login with your new password.', category='success')
                return redirect(url_for('auth.login'))
            else:
                flash('User not found. Please contact support.', category='error')
                
    return render_template('reset_password.html', token=token, user=current_user)


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


# Utility functions
def send_verification_email_to_user(user, token):
    """Sends verification email to user"""
    verification_link = url_for('auth.verify_email', token=token, _external=True)
    # TODO: Implement actual email sending here
    print(f"VERIFICATION EMAIL: To: {user.email}")
    print(f"Verification Link: {verification_link}")


def send_password_reset_email_to_user(user, token):
    """Sends password reset email to user"""
    reset_link = url_for('auth.reset_password', token=token, _external=True)
    # TODO: Implement actual email sending here
    print(f"PASSWORD RESET EMAIL: To: {user.email}")
    print(f"Reset Link: {reset_link}")


# API routes for AJAX authentication
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