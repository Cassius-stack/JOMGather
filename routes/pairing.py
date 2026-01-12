"""
Pairing routes - Random Search, Friend Search, Trial Sessions
"""

from flask import Blueprint, render_template, request, redirect, url_for

pairing_bp = Blueprint('pairing', __name__)

@pairing_bp.route('/random-search')
def random_search():
    """Random search for matching users based on interests."""
    # TODO: Implement matching algorithm
    return render_template('pairing/random_search.html')

@pairing_bp.route('/friend-search')
def friend_search():
    """Search for specific users by name."""
    return render_template('pairing/friend_search.html')

@pairing_bp.route('/trial-session/<int:pair_id>')
def trial_session(pair_id):
    """Trial session to evaluate compatibility."""
    # TODO: Fetch pair details
    return render_template('pairing/trial_session.html', pair_id=pair_id)

@pairing_bp.route('/confirm-pair/<int:pair_id>', methods=['POST'])
def confirm_pair(pair_id):
    """Confirm a pairing after trial session."""
    # TODO: Update pair status in database
    return redirect(url_for('pairing.random_search'))

@pairing_bp.route('/find-new/<int:pair_id>', methods=['POST'])
def find_new(pair_id):
    """Decline current match and find new pair."""
    # TODO: Update pair status and find new match
    return redirect(url_for('pairing.random_search'))
