"""
Support Swap routes - Support Swap feature (Zongrong's feature)
Support Library, Support Assignment, Support Match
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.supabase_db import get_supabase

support_swap_bp = Blueprint('support_swap', __name__)

@support_swap_bp.route('/ss_profile', methods=['GET', 'POST'])
def ss_profile():
    """View and manage user's skills profile."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    # Handle adding a new skill
    if request.method == 'POST':
        skill_name = request.form.get('skill_name')
        category = request.form.get('category', 'general')
        
        if skill_name:
            try:
                supabase.table('user_skills').insert({
                    'user_id': user_id,
                    'skill_name': skill_name,
                    'category': category
                }).execute()
                flash('Skill added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding skill: {str(e)}', 'error')
        
        return redirect(url_for('support_swap.ss_profile'))
    
    # Fetch user's skills
    try:
        response = supabase.table('user_skills').select('*').eq('user_id', user_id).execute()
        skills = response.data
    except Exception as e:
        skills = []
        flash(f'Error fetching skills: {str(e)}', 'error')
    
    return render_template('support_swap/ss_profile.html', skills=skills)

@support_swap_bp.route('/delete_skill/<int:skill_id>', methods=['POST'])
def delete_skill(skill_id):
    """Delete a user skill."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        # Only delete if user owns the skill
        supabase.table('user_skills').delete().eq('id', skill_id).eq('user_id', user_id).execute()
        flash('Skill deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting skill: {str(e)}', 'error')
    
    return redirect(url_for('support_swap.ss_profile'))

@support_swap_bp.route('/ss_activity')
def ss_activity():
    """Browse available support swaps."""
    # TODO: Fetch support swaps from database
    return render_template('support_swap/ss_activity.html')

@support_swap_bp.route('/ss_market')
def ss_market():
    """Skills Market - Browse available help requests from other users."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    supabase = get_supabase()
    
    try:
        # Fetch all open requests from OTHER users (not current user)
        response = supabase.table('help_requests').select(
            '*, users(username)'
        ).neq('user_id', user_id).eq('status', 'open').order('created_at', desc=True).execute()
        requests = response.data
    except Exception as e:
        requests = []
        flash(f'Error fetching requests: {str(e)}', 'error')
    
    return render_template('support_swap/ss_market.html', requests=requests)

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
        
        if title:
            try:
                supabase.table('help_requests').insert({
                    'user_id': user_id,
                    'title': title,
                    'description': description,
                    'request_type': request_type,
                    'duration_hours': int(duration_hours) if duration_hours else 1,
                    'location': location,
                    'scheduled_date': scheduled_date if scheduled_date else None
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
    
    return render_template('support_swap/ss_post.html', my_requests=my_requests)

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
                         completed_matches=completed_matches)

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
    
    return redirect(url_for('support_swap.ss_market'))

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
