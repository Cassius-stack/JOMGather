"""
Seed script to create the global Admin account.
Run once: python scripts/seed_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from werkzeug.security import generate_password_hash
from utils.supabase_db import get_supabase, fetch_one, insert
import uuid

def seed_admin():
    """Create the Admin account if it doesn't already exist."""
    supabase = get_supabase()
    
    # Check if admin already exists
    existing = fetch_one('users', username='Admin')
    if existing:
        print(f"Admin account already exists (user_id={existing['user_id']}). Skipping.")
        return
    
    admin_data = {
        'username': 'Admin',
        'email': 'dev_admin',
        'user_type': 'admin',
        'auth_id': str(uuid.uuid4()),
        'password_hash': generate_password_hash('admin123'),
        'age': None,
        'region': None,
        'hobbies': [],
        'skills': []
    }
    
    try:
        new_admin = insert('users', admin_data)
        if new_admin:
            print(f"Admin account created successfully! user_id={new_admin['user_id']}")
        else:
            print("Failed to create admin account (no data returned).")
    except Exception as e:
        import traceback
        print(f"ERROR inserting admin: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    seed_admin()
