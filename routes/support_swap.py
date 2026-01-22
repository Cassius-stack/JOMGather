"""
Support Swap routes - Support Swap feature (Zongrong's feature)
Support Library, Support Assignment, Support Match
"""

from flask import Blueprint, render_template, request, redirect, url_for

support_swap_bp = Blueprint('support_swap', __name__)

@support_swap_bp.route('/ss_profile')
def ss_profile():
    """Browse available support swaps."""
    # TODO: Fetch support swaps from database
    return render_template('support_swap/ss_profile.html')

@support_swap_bp.route('/ss_activity')
def ss_activity():
    """Browse available support swaps."""
    # TODO: Fetch support swaps from database
    return render_template('support_swap/ss_activity.html')

@support_swap_bp.route('/ss_match', methods=['GET', 'POST'])
def ss_match():
    """View support matches and handle match requests."""
    if request.method == 'POST':
        # TODO: Update user support skills in database
        pass
    # TODO: Find matching users based on support needs
    return render_template('support_swap/ss_match.html')

@support_swap_bp.route('/request/<int:user_id>', methods=['POST'])
def request_support_match(user_id):
    """Request a support swap with a user."""
    # TODO: Create support match request
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/accept/<int:match_id>', methods=['POST'])
def accept_support_match(match_id):
    """Accept a support swap request."""
    # TODO: Update match status
    return redirect(url_for('support_swap.ss_match'))

@support_swap_bp.route('/complete/<int:match_id>', methods=['POST'])
def complete_support_session(match_id):
    """Mark a support session as complete and earn rewards."""
    # TODO: Award points and badges
    return redirect(url_for('support_swap.ss_match'))
