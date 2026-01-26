"""
Profile routes - View, Edit, Settings (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/view')
@profile_bp.route('/view/<int:user_id>')
def view_profile(user_id=None):
    """View a user's profile."""
    from utils.supabase_db import fetch_one
    
    # If no user_id provided, show current logged-in user's profile
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            flash("Please log in to view your profile.", "warning")
            return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    if not user:
        return "User not found", 404
        
    return render_template('profile/view_profile.html', user=user)

@profile_bp.route('/edit', methods=['GET', 'POST'])
def edit_personal():
    """Edit current user's personal info."""
    from utils.supabase_db import fetch_one, update
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username')
            email = request.form.get('email')
            age = request.form.get('age')
            
            # Determine user_type based on age
            try:
                user_age = int(age) if age else 0
                user_type = 'senior' if user_age > 55 else 'youth'
            except ValueError:
                user_type = 'youth'
            
            # Update database
            update('users', {
                'username': username,
                'email': email,
                'age': int(age) if age else None,
                'user_type': user_type
            }, user_id=user_id)
            
            # Update session
            session['username'] = username
            session['user_type'] = user_type
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            print(f"Profile Update Error: {e}")
            flash(f"Error updating profile: {e}", "danger")
    
    return render_template('profile/edit_personal.html', user=user)

@profile_bp.route('/edit-social', methods=['GET', 'POST'])
def edit_social():
    """Edit current user's social profile (region, hobbies, skills)."""
    from utils.supabase_db import fetch_one, update
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            region = request.form.get('region')
            hobbies_str = request.form.get('hobbies', '')
            skills_str = request.form.get('skills', '')
            
            # Convert comma-separated strings to lists
            hobbies = [h.strip() for h in hobbies_str.split(',') if h.strip()]
            skills = [s.strip() for s in skills_str.split(',') if s.strip()]
            
            # Update database
            update('users', {
                'region': region if region else None,
                'hobbies': hobbies,
                'skills': skills
            }, user_id=user_id)
            
            flash("Social profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            print(f"Social Profile Update Error: {e}")
            flash(f"Error updating profile: {e}", "danger")
    
    return render_template('profile/edit_social.html', user=user)

@profile_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings page - only accessible to logged-in user for their own settings."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to access settings.", "warning")
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # TODO: Update settings in database
        pass
    return render_template('profile/settings.html')

@profile_bp.route('/delete-account', methods=['POST'])
def delete_account():
    """Delete user account and all their data."""
    from utils.supabase_db import get_supabase
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for('auth.login'))
    
    try:
        supabase = get_supabase()
        
        # Delete related data first (to avoid foreign key constraints)
        # Delete messages sent by user
        try:
            supabase.table('messages').delete().eq('sender_id', user_id).execute()
        except:
            pass
        
        # Delete messages received by user
        try:
            supabase.table('messages').delete().eq('receiver_id', user_id).execute()
        except:
            pass
        
        # Delete friendships (delete ALL where this user is involved)
        try:
            supabase.table('friendships').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Error deleting friendships (user_id): {e}")
        
        try:
            supabase.table('friendships').delete().eq('user_id_2', user_id).execute()
        except Exception as e:
            print(f"Error deleting friendships (user_id_2): {e}")
        
        # Delete friend requests
        try:
            supabase.table('friend_requests').delete().eq('sender_id', user_id).execute()
            supabase.table('friend_requests').delete().eq('receiver_id', user_id).execute()
        except:
            pass
        
        # Delete slice of life entries
        try:
            supabase.table('slice_of_life').delete().eq('user_id', user_id).execute()
        except:
            pass
        
        # Delete support swap requests
        try:
            supabase.table('support_swap_requests').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Error deleting support_swap_requests: {e}")
        
        # Delete replies
        try:
            supabase.table('replies').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Error deleting replies: {e}")
        
        # Delete posts/questions (Ask a Grandfriend)
        try:
            supabase.table('posts').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Error deleting posts: {e}")
        
        try:
            supabase.table('questions').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Error deleting questions: {e}")
        
        # Finally, delete the user
        supabase.table('users').delete().eq('user_id', user_id).execute()
        
        # Clear the session
        session.clear()
        
        flash("Your account has been deleted successfully.", "info")
        return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"Delete Account Error: {e}")
        flash(f"Error deleting account: {e}", "danger")
        return redirect(url_for('profile.settings'))
