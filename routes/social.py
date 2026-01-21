"""
Social routes - Social features, Chat, AskAGrandfriend (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils.helpers import get_db_connection

social_bp = Blueprint('social', __name__)


def get_current_user_id():
    """Get current user ID from query parameter (for testing) or session."""
    return int(request.args.get('user', 1))


@social_bp.route('/')
def social_hub():
    """Main social/chat hub."""
    return render_template('social/social_hub.html')

# === CHAT API ENDPOINTS ===

@social_bp.route('/api/contacts')
def get_contacts():
    """Get list of all contacts for the current user."""
    current_user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Get all users except current user, with their last message if any
    contacts = conn.execute('''
        SELECT u.user_id, u.username, 
               (SELECT content FROM messages 
                WHERE (sender_id = u.user_id AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = u.user_id)
                ORDER BY sent_at DESC LIMIT 1) as last_message,
               (SELECT sender_id FROM messages 
                WHERE (sender_id = u.user_id AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = u.user_id)
                ORDER BY sent_at DESC LIMIT 1) as last_sender_id,
               (SELECT sent_at FROM messages 
                WHERE (sender_id = u.user_id AND receiver_id = ?)
                   OR (sender_id = ? AND receiver_id = u.user_id)
                ORDER BY sent_at DESC LIMIT 1) as last_message_time
        FROM users u
        WHERE u.user_id != ?
        ORDER BY last_message_time DESC NULLS LAST
    ''', (current_user_id, current_user_id, current_user_id, current_user_id,
          current_user_id, current_user_id, current_user_id)).fetchall()
    
    conn.close()
    
    result = []
    for c in contacts:
        preview = ''
        if c['last_message']:
            prefix = 'You: ' if c['last_sender_id'] == current_user_id else ''
            preview = f"{prefix}{c['last_message'][:30]}"
        result.append({
            'id': c['user_id'],
            'name': c['username'],
            'lastMessage': preview,
            'status': 'Active now'
        })
    
    return jsonify(result)

@social_bp.route('/api/messages/<int:contact_id>')
def get_messages(contact_id):
    """Get messages between current user and a contact."""
    current_user_id = get_current_user_id()
    conn = get_db_connection()
    
    messages = conn.execute('''
        SELECT message_id, sender_id, receiver_id, content, sent_at, read
        FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY sent_at ASC
    ''', (current_user_id, contact_id, contact_id, current_user_id)).fetchall()
    
    conn.close()
    
    return jsonify([{
        'id': m['message_id'],
        'type': 'sent' if m['sender_id'] == current_user_id else 'received',
        'text': m['content'],
        'time': m['sent_at']
    } for m in messages])

@social_bp.route('/api/messages', methods=['POST'])
def send_message():
    """Send a new message."""
    current_user_id = get_current_user_id()
    data = request.get_json()
    receiver_id = data.get('receiverId')
    content = data.get('content')
    
    if not receiver_id or not content:
        return jsonify({'error': 'Missing receiverId or content'}), 400
    
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, content)
        VALUES (?, ?, ?)
    ''', (current_user_id, receiver_id, content))
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': message_id,
        'type': 'sent',
        'text': content,
        'success': True
    })

# === OTHER SOCIAL ROUTES ===

@social_bp.route('/<int:group_id>')
def group_detail(group_id):
    """View a specific social group."""
    return render_template('social/group_detail.html', group_id=group_id)

@social_bp.route('/create', methods=['GET', 'POST'])
def create_group():
    """Create a new social group."""
    if request.method == 'POST':
        pass
    return render_template('social/social_hub.html')

@social_bp.route('/join/<int:group_id>', methods=['POST'])
def join_group(group_id):
    """Join a social group."""
    return redirect(url_for('social.group_detail', group_id=group_id))

@social_bp.route('/ask-grandfriend')
def ask_grandfriend():
    """AskAGrandfriend forum."""
    return render_template('social/ask_grandfriend.html')

@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        pass
    return render_template('social/ask_grandfriend.html')
