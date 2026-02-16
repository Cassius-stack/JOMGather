"""
Support Swap routes - Support Swap feature (Zongrong's feature)
Support Library, Support Assignment, Support Match
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.supabase_db import get_supabase

support_swap_bp = Blueprint('support_swap', __name__)

def get_user_region(user_id):
    """Helper function to fetch user's region from database."""
    if not user_id:
        return None
    try:
        supabase = get_supabase()
        response = supabase.table('users').select('region').eq('user_id', user_id).limit(1).execute()
        if response.data:
            return response.data[0].get('region')
    except Exception as e:
        print(f"Error fetching user region: {e}")
    return None

@support_swap_bp.route('/ss_dashboard', methods=['GET', 'POST'])
def ss_dashboard():
    """Combined dashboard - Profile and Skills Market."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    # Fetch current user profile (including skills)
    user_profile = None
    skills = []
    try:
        profile_response = supabase.table('users').select('username, skills, region').eq('user_id', user_id).limit(1).execute()
        if profile_response.data:
            user_profile = profile_response.data[0]
            skills = user_profile.get('skills') or []
    except Exception as e:
        print(f"Error fetching user profile: {e}")
    
    # Handle adding a new skill
    if request.method == 'POST':
        skill_name = request.form.get('skill_name')
        
        if skill_name and skill_name not in skills:
            try:
                # Add new skill to the existing skills array
                updated_skills = skills + [skill_name]
                supabase.table('users').update({'skills': updated_skills}).eq('user_id', user_id).execute()
                flash('Skill added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding skill: {str(e)}', 'error')
        elif skill_name in skills:
            flash('This skill already exists!', 'warning')
        
        return redirect(url_for('support_swap.ss_dashboard'))
    
    # Calculate VIA hours from completed support sessions (where user was the helper)
    via_hours = 0
    try:
        # Get completed matches where user is the helper, join with help_requests to get duration
        completed_response = supabase.table('support_matches').select(
            'help_requests(duration_hours)'
        ).eq('helper_id', user_id).eq('status', 'completed').execute()
        
        if completed_response.data:
            for match in completed_response.data:
                if match.get('help_requests') and match['help_requests'].get('duration_hours'):
                    via_hours += match['help_requests']['duration_hours']
    except Exception as e:
        print(f"Error calculating VIA hours: {e}")
    
    # Fetch help requests for Skills Market (from OTHER users)
    requests = []
    try:
        response = supabase.table('help_requests').select(
            '*, users(username)'
        ).neq('user_id', user_id).eq('status', 'open').order('created_at', desc=True).execute()
        requests = response.data
    except Exception as e:
        print(f"Error fetching requests: {e}")
    
    return render_template('support_swap/ss_dashboard.html', 
                          skills=skills, 
                          user_profile=user_profile,
                          user_region=get_user_region(user_id),
                          via_hours=via_hours,
                          requests=requests)

@support_swap_bp.route('/delete_skill', methods=['POST'])
def delete_skill():
    """Delete a user skill from the users.skills array."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    # Get skill name from form
    skill_name = request.form.get('skill_name')
    if not skill_name:
        flash('No skill specified', 'error')
        return redirect(url_for('support_swap.ss_dashboard'))
    
    supabase = get_supabase()
    
    try:
        # Fetch current skills
        response = supabase.table('users').select('skills').eq('user_id', user_id).limit(1).execute()
        if response.data:
            current_skills = response.data[0].get('skills') or []
            # Remove the skill from the list
            if skill_name in current_skills:
                current_skills.remove(skill_name)
                supabase.table('users').update({'skills': current_skills}).eq('user_id', user_id).execute()
                flash('Skill deleted successfully!', 'success')
            else:
                flash('Skill not found', 'warning')
    except Exception as e:
        flash(f'Error deleting skill: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_dashboard'))

@support_swap_bp.route('/ss_activity')
def ss_activity():
    """Browse available support swaps."""
    user_id = session.get('user_id')
    user_region = get_user_region(user_id)
    return render_template('support_swap/ss_activity.html', user_region=user_region)

    return redirect(url_for('support_swap.ss_dashboard'))

@support_swap_bp.route('/ss_post', methods=['GET', 'POST'])
def ss_post():
    """Post a support request."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        request_type = request.form.get('request_type', 'assistance')
        duration_hours = request.form.get('duration_hours', 1)
        location = request.form.get('location')
        scheduled_date = request.form.get('scheduled_date')
        skills_needed = request.form.get('skills_needed')
        
        if title:
            try:
                supabase.table('help_requests').insert({
                    'user_id': user_id,
                    'title': title,
                    'description': description,
                    'request_type': request_type,
                    'duration_hours': int(duration_hours) if duration_hours else 1,
                    'location': location,
                    'scheduled_date': scheduled_date if scheduled_date else None,
                    'skills_needed': skills_needed
                }).execute()
                flash('Request posted successfully!', 'success')
            except Exception as e:
                flash(f'Error posting request: {str(e)}', 'error')
        
        return redirect(url_for('support_swap.ss_post'))
    
    # Fetch user's own requests
    try:
        response = supabase.table('help_requests').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        my_requests = response.data
    except Exception as e:
        my_requests = []
        flash(f'Error fetching your requests: {str(e)}', 'error')
    
    return render_template('support_swap/ss_post.html', my_requests=my_requests, user_region=get_user_region(user_id))

@support_swap_bp.route('/ss_match', methods=['GET', 'POST'])
def ss_match():
    """View support matches and handle match requests."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        # Fetch matches where user is the helper
        helper_response = supabase.table('support_matches').select(
            '*, help_requests(title, description, location, users(username))'
        ).eq('helper_id', user_id).order('created_at', desc=True).execute()
        
        # Fetch matches where user is the requester (from their help requests)
        my_requests = supabase.table('help_requests').select('id').eq('user_id', user_id).execute()
        request_ids = [r['id'] for r in my_requests.data]
        
        requester_matches = []
        if request_ids:
            req_response = supabase.table('support_matches').select(
                '*, help_requests(title, description, location), users!support_matches_helper_id_fkey(username)'
            ).in_('request_id', request_ids).order('created_at', desc=True).execute()
            requester_matches = req_response.data
        
        # Separate active and completed
        all_matches = helper_response.data + requester_matches
        active_matches = [m for m in all_matches if m['status'] in ['pending', 'accepted']]
        completed_matches = [m for m in all_matches if m['status'] in ['completed', 'cancelled']]
        
    except Exception as e:
        active_matches = []
        completed_matches = []
        flash(f'Error fetching matches: {str(e)}', 'error')
    
    return render_template('support_swap/ss_match.html', 
                         active_matches=active_matches, 
                         completed_matches=completed_matches,
                         user_region=get_user_region(user_id))

@support_swap_bp.route('/offer/<int:request_id>', methods=['POST'])
def offer_help(request_id):
    """Offer to help with a request."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        # Check if user already offered help for this request
        existing = supabase.table('support_matches').select('id').eq('request_id', request_id).eq('helper_id', user_id).execute()
        
        if existing.data:
            flash('You have already offered to help with this request!', 'warning')
        else:
            supabase.table('support_matches').insert({
                'request_id': request_id,
                'helper_id': user_id,
                'status': 'pending'
            }).execute()
            flash('Your offer to help has been sent!', 'success')
    except Exception as e:
        flash(f'Error offering help: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/delete/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    """Delete a help request."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        # Only delete if user owns the request
        supabase.table('help_requests').delete().eq('id', request_id).eq('user_id', user_id).execute()
        flash('Request deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting request: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_post'))

@support_swap_bp.route('/accept/<int:match_id>', methods=['POST'])
def accept_support_match(match_id):
    """Accept a support swap request."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        supabase.table('support_matches').update({'status': 'accepted'}).eq('id', match_id).execute()
        flash('Match accepted!', 'success')
    except Exception as e:
        flash(f'Error accepting match: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/complete/<int:match_id>', methods=['POST'])
def complete_support_session(match_id):
    """Mark a support session as complete."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        from datetime import datetime
        supabase.table('support_matches').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }).eq('id', match_id).execute()
        flash('Session marked as complete! Thank you for helping!', 'success')
    except Exception as e:
        flash(f'Error completing session: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/cancel/<int:match_id>', methods=['POST'])
def cancel_match(match_id):
    """Cancel a support match."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        from datetime import datetime
        supabase.table('support_matches').update({
            'status': 'cancelled',
            'completed_at': datetime.now().isoformat()
        }).eq('id', match_id).execute()
        flash('Match cancelled successfully.', 'info')
    except Exception as e:
        flash(f'Error cancelling match: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/verify/<int:match_id>')
def verify_match(match_id):
    """Verification page — shown when partner scans the QR code."""
    supabase = get_supabase()
    
    try:
        match_data = supabase.table('support_matches').select(
            '*, help_requests(title, description, location, duration_hours, users(username))'
        ).eq('id', match_id).execute()
        
        if not match_data.data:
            flash('Match not found.', 'error')
            return redirect(url_for('support_swap.ss_match'))
        
        match = match_data.data[0]
        
        # Get helper username
        helper = supabase.table('users').select('username').eq('user_id', match['helper_id']).execute()
        helper_name = helper.data[0]['username'] if helper.data else 'Unknown'
        
        return render_template('support_swap/ss_verify.html', 
                             match=match, 
                             helper_name=helper_name)
    except Exception as e:
        flash(f'Error loading verification: {str(e)}', 'error')
        return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/confirm/<int:match_id>', methods=['POST'])
def confirm_match(match_id):
    """Confirm completion from the verification page."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to confirm.", "warning")
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        from datetime import datetime
        supabase.table('support_matches').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }).eq('id', match_id).execute()
        flash('Session verified and marked as complete! Thank you!', 'success')
    except Exception as e:
        flash(f'Error confirming session: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_match'))
