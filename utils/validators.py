"""
Form validation helpers for MySavvyGranny
"""

import re

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, None

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, None

def validate_username(username):
    """Validate username format."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if len(username) > 20:
        return False, "Username cannot exceed 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, None

def validate_required(value, field_name):
    """Validate that a field is not empty."""
    if not value or not str(value).strip():
        return False, f"{field_name} is required"
    return True, None

def validate_max_length(value, max_length, field_name):
    """Validate that a field does not exceed max length."""
    if len(str(value)) > max_length:
        return False, f"{field_name} cannot exceed {max_length} characters"
    return True, None
