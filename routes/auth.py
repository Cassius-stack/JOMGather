"""
Authentication routes - Login, Register, Onboarding
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.supabase_db import get_supabase, insert, fetch_one, upload_file
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration directly."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate required fields
        if not username or not email or not password:
            flash("Please fill in all fields.", "danger")
            return render_template('auth/register.html')
        
        # Block reserved admin username
        if username.strip().lower() == 'admin':
            flash("This username is reserved. Please choose a different one.", "danger")
            return render_template('auth/register.html')
        
        # Default user type (can be updated later in profile settings)
        user_type = 'youth'
        
        # === DEV BYPASS: Skip Supabase if email starts with 'dev_' ===
        if email.startswith('dev_'):
            try:
                user_uuid = str(uuid.uuid4())
                hashed_password = generate_password_hash(password)
                
                new_user = insert('users', {
                    'username': username,
                    'email': email,
                    'user_type': user_type,
                    'auth_id': user_uuid,
                    'password_hash': hashed_password,
                    'age': None,
                    'region': None,
                    'hobbies': [],
                    'skills': []
                })
                
                session['user_id'] = new_user['user_id']
                session['username'] = new_user['username']
                session['user_type'] = new_user['user_type']
                
                flash("Account created! Let's complete your profile.", "success")
                return redirect(url_for('auth.onboarding'))
                
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
            
            if not auth_response.user:
                flash("Registration failed. Please try again.", "danger")
                return render_template('auth/register.html')
                 
            user_uuid = auth_response.user.id

            # 2. Create user in Internal Users Table
            hashed_password = generate_password_hash(password)
            
            new_user = insert('users', {
                'username': username,
                'email': email,
                'user_type': user_type,
                'auth_id': user_uuid,
                'password_hash': hashed_password,
                'age': None,
                'region': None,
                'hobbies': [],
                'skills': []
            })

            # Log the user in automatically
            session['user_id'] = new_user['user_id']
            session['username'] = new_user['username']
            session['user_type'] = new_user['user_type']
            
            flash("Account created! Let's complete your profile.", "success")
            return redirect(url_for('auth.onboarding'))

        except Exception as e:
            print(f"Registration Error: {e}")
            traceback.print_exc()
            flash(f"Error: {e}", "danger")
    
    return render_template('auth/register.html')


@auth_bp.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """Handle profile completion for newly registered users."""
    
    # User must be logged in to access onboarding
    if 'user_id' not in session:
        flash("Please register or log in first.", "warning")
        return redirect(url_for('auth.register'))
    
    if request.method == 'POST':
        age = request.form.get('age')
        region = request.form.get('region')
        hobbies = request.form.getlist('hobbies')
        skills = request.form.getlist('skills')
        
        # Determine user type based on age
        try:
            user_age = int(age) if age else 0
            user_type = 'senior' if user_age > 55 else 'youth'
        except ValueError:
            user_type = 'youth'
        
        # Never allow user_type to be set to 'admin' via onboarding
        if session.get('user_type') == 'admin':
            user_type = 'admin'
        
        # Handle profile photo upload
        profile_photo_url = None
        photo_file = request.files.get('profile_photo')
        if photo_file and photo_file.filename:
            try:
                import os
                ext = os.path.splitext(photo_file.filename)[1].lower() or '.jpg'
                storage_path = f"avatars/{session['user_id']}{ext}"
                profile_photo_url = upload_file(photo_file, bucket='avatars', path=storage_path)
            except Exception as upload_err:
                print(f"Photo Upload Error: {upload_err}")
                flash("Profile saved, but photo upload failed. You can add one later.", "warning")
        
        try:
            # Update the user's profile with onboarding data
            from utils.supabase_db import update
            
            update_data = {
                'age': age,
                'region': region,
                'hobbies': hobbies if hobbies else [],
                'skills': skills if skills else [],
                'user_type': user_type
            }
            if profile_photo_url:
                update_data['profile_photo_url'] = profile_photo_url
            
            update('users', update_data, user_id=session['user_id'])
            
            # Update session with new user type
            session['user_type'] = user_type
            
            flash(f"Profile complete! Welcome to JomGather!", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Onboarding Error: {e}")
            traceback.print_exc()
            flash(f"Error saving profile: {e}", "danger")
    
    # GET request - display onboarding form
    return render_template('auth/onboarding.html')


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
                if internal_user and internal_user.get('is_deleted'):
                     flash("This account has been deleted.", "danger")
                     return render_template('auth/login.html')
                     
                if internal_user:
                    # Check for active ban
                    banned_until_str = internal_user.get('boomerang_banned_until')
                    if banned_until_str:
                        import datetime
                        try:
                            banned_until = datetime.datetime.fromisoformat(banned_until_str.replace('Z', '+00:00'))
                            if datetime.datetime.now(datetime.timezone.utc) < banned_until:
                                session.clear()
                                flash("Your account is temporarily suspended due to multiple community reports.", "danger")
                                return render_template('auth/login.html')
                        except Exception as e:
                            print(f"Error parsing ban date at dev login: {e}")
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
            
            if internal_user and internal_user.get('is_deleted'):
                session.clear()
                flash("This account has been deleted.", "danger")
                return render_template('auth/login.html')
            
            if internal_user:
                # Check for active ban
                banned_until_str = internal_user.get('boomerang_banned_until')
                if banned_until_str:
                    import datetime
                    try:
                        banned_until = datetime.datetime.fromisoformat(banned_until_str.replace('Z', '+00:00'))
                        if datetime.datetime.now(datetime.timezone.utc) < banned_until:
                            session.clear()
                            flash("Your account is temporarily suspended due to multiple community reports.", "danger")
                            return render_template('auth/login.html')
                    except Exception as e:
                        print(f"Error parsing ban date at login: {e}")
                
                # 3. Create Session with Internal ID
                session.clear() # Clear any old session data first
                session['user_id'] = internal_user['user_id']
                session['username'] = internal_user['username']
                session['user_type'] = internal_user['user_type']
                
                # Make session permanent (lasts 31 days by default)
                session.permanent = True

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
        # Sign out from Supabase (clears server-side token if any)
        get_supabase().auth.sign_out()
    except:
        pass # Ignore if already logged out on server
        
    # Clear Flask session completely
    session.clear()

    # Force session to be marked as modified to ensure cookie is cleared
    session.modified = True

    # Flash message might not persist if session is cleared, so we rely on the redirect
    # or re-set it after clearing but before response
    # However, flash() uses session, so calling it AFTER clear() is correct
    flash("You have been logged out.", "info")

    # Redirect to LOGIN directly, not index, to avoid any landing page logic
    # that might check for session presence
    return redirect(url_for('auth.login'))
