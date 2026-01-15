"""
Social routes - Social features, AskAGrandfriend (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for

social_bp = Blueprint('social', __name__)

@social_bp.route('/')
def social_hub():
    """List all social groups."""
    # TODO: Fetch social groups from database
    return render_template('social/social_hub.html')

@social_bp.route('/<int:group_id>')
def group_detail(group_id):
    """View a specific social group."""
    # TODO: Fetch group details
    return render_template('social/group_detail.html', group_id=group_id)

@social_bp.route('/create', methods=['GET', 'POST'])
def create_group():
    """Create a new social group."""
    if request.method == 'POST':
        # TODO: Save group to database
        pass
    return render_template('social/social_hub.html')

@social_bp.route('/join/<int:group_id>', methods=['POST'])
def join_group(group_id):
    """Join a social group."""
    # TODO: Add user to group
    return redirect(url_for('social.group_detail', group_id=group_id))

@social_bp.route('/ask-grandfriend')
def ask_grandfriend():
    """AskAGrandfriend forum."""
    return render_template('social/ask_grandfriend.html')

@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        # TODO: Save question to database
        pass
    return render_template('social/ask_grandfriend.html')
