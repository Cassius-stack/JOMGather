"""
Profile routes - View, Edit, Settings (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/view/<int:user_id>')
def view_profile(user_id):
    """View a user's profile."""
    from utils.supabase_db import fetch_one
    
    user = fetch_one('users', user_id=user_id)
    if not user:
        return "User not found", 404
        
    return render_template('profile/view_profile.html', user=user)

@profile_bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    """Edit current user's profile."""
    if request.method == 'POST':
        # TODO: Update profile in database
        pass
    return render_template('profile/edit_profile.html')

@profile_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings page."""
    if request.method == 'POST':
        # TODO: Update settings in database
        pass
    return render_template('profile/settings.html')
