from . import db
from .models import User, Course, Lesson, Category, Achievement, PasswordReset, EmailVerification
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
import secrets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_to_db(obj):
    try:
        db.session.add(obj)
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        return False
    
def update_db():
    """
    Commit changes to the database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        return False


def get_user_by_email(email):
    """
    Retrieve a user by email address
    
    Args:
        email (str): User's email address
        
    Returns:
        User: User object if found, None otherwise
    """
    try:
        return User.query.filter_by(email=email).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving user by email: {str(e)}")
        return None
    
def get_user_by_id(user_id):
    """
    Get a user by ID
    
    Args:
        user_id (int): User's ID
        
    Returns:
        User: User object if found, None otherwise
    """
    try:
        return User.query.get(user_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving user by ID: {str(e)}")
        return None
    
def delete_from_db(obj):
    """
    Generic function to delete an object from the database
    
    Args:
        obj: SQLAlchemy model instance to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        return False
    
def create_user(email, first_name, last_name, password_hash, username=None):
    """
    Create a new user
    
    Args:
        email (str): User's email
        first_name (str): User's first name
        last_name (str): User's last name
        password_hash (str): Hashed password
        username (str, optional): Username (defaults to None)
        
    Returns:
        User: The created user object if successful, None otherwise
    """
    try:
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password_hash,
            username=username or email.split('@')[0],
            is_active=True,
            is_verified=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(new_user)
        db.session.commit()
        return new_user
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating user: {str(e)}")
        return None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating user: {str(e)}")
        return None
    
def verify_email_token(token):
    try :
        verification = EmailVerification.query.filter_by(token=token).first()
        if verification and verification.expires_at > datetime.now():
            return verification.user
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error verifying email token: {str(e)}")
        return None
    
def create_email_verification_token(user_id, expiry_hours=24):
    """
    Create a new email verification token
    
    Args:
        user_id (int): User ID
        expiry_hours (int): Token expiry in hours
        
    Returns:
        str: Generated token if successful, None otherwise
    """
    try:
        token = secrets.token_urlsafe(16)
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        verification = EmailVerification(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        db.session.add(verification)
        db.session.commit()
        return token
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating email verification token: {str(e)}")
        return None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating email verification token: {str(e)}")
        return None
    
def get_user_by_username(username):
    try:
        return User.query.filter_by(username=username).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving user by username: {str(e)}")
        return None

def update_user_profile(user_id, data):
    """
    Update a user's profile information
    
    Args:
        user_id (int): ID of the user to update
        data (dict): Dictionary containing fields to update
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        user = get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
            
        # Update fields based on data dictionary
        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.now()
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating user profile: {str(e)}")
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error updating user profile: {str(e)}")
        return False

def create_password_reset_token(user_id, expiry_hours=1):
    """
    Create a password reset token for a user
    
    Args:
        user_id (int): ID of the user
        expiry_hours (int): Token expiry time in hours
        
    Returns:
        str: The generated token, or None if an error occurred
    """
    try:
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        # Create new PasswordReset record
        reset_request = PasswordReset(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        db.session.add(reset_request)
        db.session.commit()
        return token
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating password reset token: {str(e)}")
        return None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating password reset token: {str(e)}")
        return None

def verify_password_reset_token(token):
    """
    Verify a password reset token
    
    Args:
        token (str): The token to verify
        
    Returns:
        PasswordReset: The reset request object if valid, None otherwise
    """
    try:
        reset_request = PasswordReset.query.filter_by(token=token).first()
        
        # Check if token exists and is not expired
        if reset_request and reset_request.expires_at > datetime.now():
            return reset_request
        
        # Token not found or expired
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error verifying password reset token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying password reset token: {str(e)}")
        return None