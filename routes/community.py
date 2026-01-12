"""
Community routes - Communities, AskAGrandfriend (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for

community_bp = Blueprint('community', __name__)

@community_bp.route('/')
def communities():
    """List all interest communities."""
    # TODO: Fetch communities from database
    return render_template('community/communities.html')

@community_bp.route('/<int:community_id>')
def community_detail(community_id):
    """View a specific community."""
    # TODO: Fetch community details
    return render_template('community/community_detail.html', community_id=community_id)

@community_bp.route('/create', methods=['GET', 'POST'])
def create_community():
    """Create a new community."""
    if request.method == 'POST':
        # TODO: Save community to database
        pass
    return render_template('community/communities.html')

@community_bp.route('/join/<int:community_id>', methods=['POST'])
def join_community(community_id):
    """Join a community."""
    # TODO: Add user to community
    return redirect(url_for('community.community_detail', community_id=community_id))

@community_bp.route('/ask-grandfriend')
def ask_grandfriend():
    """AskAGrandfriend forum."""
    return render_template('community/ask_grandfriend.html')

@community_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        # TODO: Save question to database
        pass
    return render_template('community/ask_grandfriend.html')
