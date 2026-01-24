"""
Authentication routes - Login, Register, Onboarding
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.supabase_db import get_supabase, insert, fetch_one
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration and link to internal DB."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        user_type = 'senior' # Default for MVP, updated in Onboarding

        # === DEV BYPASS: Skip Supabase if email starts with 'dev_' ===
        if email.startswith('dev_'):
             try:
                # Local "Fake" Auth
                user_uuid = str(uuid.uuid4())
                hashed_password = generate_password_hash(password)
                
                new_user = insert('users', {
                    'username': username,
                    'email': email,
                    'user_type': user_type,
                    'auth_id': user_uuid,
                    'password_hash': hashed_password
                })
                
                # Create coins row for new user (starts with 0 coins)
                insert('coins', {'user_id': new_user['user_id'], 'total_coins': 0})
                
                flash("Dev Account created! Logged in locally.", "success")
                session['user_id'] = new_user['user_id']
                session['username'] = new_user['username']
                session['user_type'] = new_user['user_type']
                return redirect(url_for('index'))
             except Exception as e:
                 print(f"Dev Register Error: {e}")
                 traceback.print_exc()
                 flash(f"Dev Error: {e}", "danger")
                 return render_template('auth/register.html')
        # =============================================================

        try:
            # 1. Create Supabase Auth User
            supabase = get_supabase()
            auth_response = supabase.auth.sign_up({
                "email": email, 
                "password": password
            })
            
            # Check if user object exists (sign up success)
            if not auth_response.user:
                 flash("Registration failed. Please try again.", "danger")
                 return redirect(url_for("auth.register"))
                 
            user_uuid = auth_response.user.id

            # 2. Link to Internal Users Table (with real hash)
            hashed_password = generate_password_hash(password)
            
            new_user = insert('users', {
                'username': username,
                'email': email,
                'user_type': user_type,
                'auth_id': user_uuid,
                'password_hash': hashed_password
            })
            
            # Create coins row for new user (starts with 0 coins)
            insert('coins', {'user_id': new_user['user_id'], 'total_coins': 0})

            flash("Account created! Please log in.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Registration Error: {e}")
            traceback.print_exc()
            flash(f"Error: {e}", "danger")
    
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login and session creation."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # === DEV BYPASS: Local Login ===
        if email.startswith('dev_'):
            try:
                internal_user = fetch_one('users', email=email)
                if internal_user and check_password_hash(internal_user.get('password_hash', ''), password):
                     session['user_id'] = internal_user['user_id']
                     session['username'] = internal_user['username']
                     session['user_type'] = internal_user['user_type']
                     flash(f"Dev Login Success: {internal_user['username']}", "success")
                     return redirect(url_for('index'))
                else:
                    flash("Invalid Dev Credentials", "danger")
                    return render_template('auth/login.html')
            except Exception as e:
                print(f"Dev Login Error: {e}")
                traceback.print_exc()
                flash("Login Error", "danger")
                return render_template('auth/login.html')
        # ===============================

        try:
            # 1. Authenticate with Supabase
            supabase = get_supabase()
            auth_response = supabase.auth.sign_in_with_password({
                "email": email, 
                "password": password
            })
            
            user_uuid = auth_response.user.id
            
            # 2. Lookup Internal User ID using auth_id
            internal_user = fetch_one('users', auth_id=user_uuid)
            
            if internal_user:
                # 3. Create Session with Internal ID (keeps legacy code working!)
                session['user_id'] = internal_user['user_id']
                session['username'] = internal_user['username']
                session['user_type'] = internal_user['user_type']
                
                flash(f"Welcome back, {internal_user['username']}!", "success")
                return redirect(url_for('index'))
            else:
                session.clear() 
                flash("Account exists but is not linked to profile. Contact support.", "warning")
                
        except Exception as e:
            print(f"Login Error: {e}")
            traceback.print_exc()
            flash("Login failed. Please check your credentials.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    try:
        get_supabase().auth.sign_out()
    except:
        pass # Ignore if already logged out on server
        
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
