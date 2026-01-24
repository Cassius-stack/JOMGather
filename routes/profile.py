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
def edit_profile():
    """Edit current user's profile."""
    from utils.supabase_db import fetch_one, update
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            age = request.form.get('age')
            region = request.form.get('region')
            hobbies = request.form.getlist('hobbies')
            skills = request.form.getlist('skills')
            
            # Update database
            update('users', {
                'age': int(age) if age else None,
                'region': region if region else None,
                'hobbies': hobbies if hobbies else [],
                'skills': skills if skills else []
            }, user_id=user_id)
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            print(f"Profile Update Error: {e}")
            flash(f"Error updating profile: {e}", "danger")
    
    return render_template('profile/edit_profile.html', user=user)

@profile_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings page."""
    if request.method == 'POST':
        # TODO: Update settings in database
        pass
    return render_template('profile/settings.html')
