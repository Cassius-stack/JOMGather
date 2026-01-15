"""
General helper functions for JOMGather
"""

import sqlite3
import os
from config import Config

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_db():
    """Initialize the database with schema."""
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'schema.sql')
    conn = get_db_connection()
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def format_datetime(dt, format_str='%d %b %Y, %I:%M %p'):
    """Format a datetime object for display."""
    if dt:
        return dt.strftime(format_str)
    return ''

def calculate_points(action):
    """Calculate points for different actions."""
    points_map = {
        'slice_of_life': 10,
        'photo_streak': 5,
        'message': 1,
        'skill_session': 15,
        'support_swap': 20,
        'community_post': 5,
        'challenge_complete': 10,
        'login_streak': 2
    }
    return points_map.get(action, 0)

def get_badge_criteria():
    """Return badge criteria for achievement system."""
    return {
        'first_story': {'name': 'Storyteller', 'requirement': 'Complete your first Slice of Life'},
        'five_streak': {'name': 'Committed', 'requirement': 'Maintain a 5-day photo streak'},
        'helper': {'name': 'Helping Hand', 'requirement': 'Complete 3 support swaps'},
        'connector': {'name': 'Social Butterfly', 'requirement': 'Join 5 communities'},
        'mentor': {'name': 'Wise Mentor', 'requirement': 'Complete 5 skill sessions'}
    }
