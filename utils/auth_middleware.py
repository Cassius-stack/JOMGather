from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """
    Decorator to ensure user is logged in.
    Checks for 'user_id' in session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
