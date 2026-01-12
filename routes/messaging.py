"""
Messaging routes - Inbox, Conversations, BOOMERang Quick Call (Cassius's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for

messaging_bp = Blueprint('messaging', __name__)

@messaging_bp.route('/inbox')
def inbox():
    """View message inbox."""
    # TODO: Fetch messages from database
    return render_template('messaging/inbox.html')

@messaging_bp.route('/conversation/<int:user_id>')
def conversation(user_id):
    """View conversation with a specific user."""
    # TODO: Fetch conversation from database
    return render_template('messaging/conversation.html', user_id=user_id)

@messaging_bp.route('/send/<int:user_id>', methods=['POST'])
def send_message(user_id):
    """Send a message to a user."""
    # TODO: Save message to database
    return redirect(url_for('messaging.conversation', user_id=user_id))

@messaging_bp.route('/boomerang')
def boomerang():
    """BOOMERang - Quick Call feature."""
    return render_template('messaging/boomerang.html')

@messaging_bp.route('/boomerang/start/<int:user_id>')
def start_call(user_id):
    """Start a quick call with a user."""
    # TODO: Initiate call
    return render_template('messaging/boomerang.html', user_id=user_id, calling=True)
