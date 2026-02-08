"""
Utility functions for interacting with APIs and managing generation status.
"""
import os
import json
from datetime import datetime

# Define a status file directory
STATUS_DIR = os.path.join("Backend", "website", "static", "status")

# Ensure the status directory exists
os.makedirs(STATUS_DIR, exist_ok=True)

def get_status_file_path(user_id):
    """Get the path to the status file for a user"""
    return os.path.join(STATUS_DIR, f"generation_status_{user_id}.json")

def get_generation_status(user_id):
    """
    Get the generation status for a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Dict containing status information or None if not found
    """
    status_file = get_status_file_path(user_id)
    
    if not os.path.exists(status_file):
        return None
        
    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def update_generation_status(user_id, percent, step, message, status="in-progress"):
    """
    Update the generation status for a user.
    
    Args:
        user_id: The ID of the user
        percent: Completion percentage (0-100)
        step: Current step number
        message: Status message
        status: Overall status (in-progress, completed, error)
        
    Returns:
        True if successful, False otherwise
    """
    status_data = {
        'status': status,
        'percent': percent,
        'step': step,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    status_file = get_status_file_path(user_id)
    
    try:
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        return True
    except IOError:
        return False 