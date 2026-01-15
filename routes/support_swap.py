"""
Support Swap routes - Support Swap feature (Zongrong's feature)
Support Library, Support Assignment, Support Match
"""

from flask import Blueprint, render_template, request, redirect, url_for

support_swap_bp = Blueprint('support_swap', __name__)

@support_swap_bp.route('/library')
def support_library():
    """Browse available support swaps."""
    # TODO: Fetch support swaps from database
    return render_template('support_swap/support_library.html')

@support_swap_bp.route('/assignment', methods=['GET', 'POST'])
def support_assignment():
    """Assign support skills to your profile."""
    if request.method == 'POST':
        # TODO: Update user support skills in database
        pass
    return render_template('support_swap/support_assignment.html')

@support_swap_bp.route('/match')
def support_match():
    """View support matches."""
    # TODO: Find matching users based on support needs
    return render_template('support_swap/support_match.html')

@support_swap_bp.route('/request/<int:user_id>', methods=['POST'])
def request_support_match(user_id):
    """Request a support swap with a user."""
    # TODO: Create support match request
    return redirect(url_for('support_swap.support_match'))

@support_swap_bp.route('/accept/<int:match_id>', methods=['POST'])
def accept_support_match(match_id):
    """Accept a support swap request."""
    # TODO: Update match status
    return redirect(url_for('support_swap.support_match'))

@support_swap_bp.route('/complete/<int:match_id>', methods=['POST'])
def complete_support_session(match_id):
    """Mark a support session as complete and earn rewards."""
    # TODO: Award points and badges
    return redirect(url_for('support_swap.support_match'))
