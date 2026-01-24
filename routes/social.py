"""
Social routes - Social features, Chat, AskAGrandfriend
Now using Supabase for database
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils.supabase_db import get_supabase, fetch_all, fetch_one, insert
import traceback

social_bp = Blueprint('social', __name__)


def get_current_user_id():
    """Get current user ID from query parameter (for testing) or session."""
    return int(request.args.get('user', 1))


@social_bp.route('/')
def social_hub():
    """Main social/chat hub."""
    return render_template('social/social_hub.html')

# === DEBUG ENDPOINT ===
@social_bp.route('/api/test')
def test_supabase():
    """Test Supabase connection."""
    try:
        from utils.supabase_db import get_supabase
        supabase = get_supabase()
        response = supabase.table('users').select('user_id, username').limit(3).execute()
        return jsonify({'success': True, 'users': response.data})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# === CHAT API ENDPOINTS ===

@social_bp.route('/api/contacts')
def get_contacts():
    """Get list of all contacts for the current user."""
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get all users except current user
        response = supabase.table('users').select('user_id, username').neq('user_id', current_user_id).execute()
        users = response.data
        
        result = []
        for user in users:
            # Get last message with this user
            try:
                msg_response = supabase.table('messages').select('*').or_(
                    f"and(sender_id.eq.{current_user_id},receiver_id.eq.{user['user_id']}),and(sender_id.eq.{user['user_id']},receiver_id.eq.{current_user_id})"
                ).order('sent_at', desc=True).limit(1).execute()
                
                last_message = msg_response.data[0] if msg_response.data else None
            except Exception as e:
                print(f"Error getting messages for user {user['user_id']}: {e}")
                last_message = None
            
            preview = ''
            if last_message:
                prefix = 'You: ' if last_message['sender_id'] == current_user_id else ''
                content = last_message.get('content', '')
                preview = f"{prefix}{content[:30]}" if content else ''
            
            result.append({
                'id': user['user_id'],
                'name': user['username'],
                'lastMessage': preview,
                'status': 'Active now'
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_contacts: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/messages/<int:contact_id>')
def get_messages(contact_id):
    """Get messages between current user and a contact."""
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get messages between the two users
        response = supabase.table('messages').select('*').or_(
            f"and(sender_id.eq.{current_user_id},receiver_id.eq.{contact_id}),and(sender_id.eq.{contact_id},receiver_id.eq.{current_user_id})"
        ).order('sent_at').execute()
        
        messages = response.data
        
        return jsonify([{
            'id': m['message_id'],
            'type': 'sent' if m['sender_id'] == current_user_id else 'received',
            'text': m['content'],
            'time': m['sent_at']
        } for m in messages])
    except Exception as e:
        print(f"Error in get_messages: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/messages', methods=['POST'])
def send_message():
    """Send a new message."""
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        receiver_id = data.get('receiverId')
        content = data.get('content')
        
        if not receiver_id or not content:
            return jsonify({'error': 'Missing receiverId or content'}), 400
        
        # Insert message using Supabase
        new_message = insert('messages', {
            'sender_id': current_user_id,
            'receiver_id': receiver_id,
            'content': content
        })
        
        if new_message:
            return jsonify({
                'id': new_message['message_id'],
                'type': 'sent',
                'text': content,
                'success': True
            })
        else:
            return jsonify({'error': 'Failed to send message'}), 500
    except Exception as e:
        print(f"Error in send_message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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
    questions = []
    try:
        supabase = get_supabase()
        result = supabase.table('questions').select('*').order('created_at', desc=True).execute()
        questions = result.data if result.data else []
    except Exception as e:
        print(f"Error fetching questions: {e}")
    return render_template('social/ask_grandfriend.html', questions=questions)

@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'tech')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        author_name = request.form.get('author_name', 'Jeremy Khoo')
        author_type = request.form.get('author_type', 'grandparent')
        
        if title:
            try:
                insert('questions', {
                    'title': title,
                    'content': content,
                    'category': category,
                    'author_name': 'Anonymous' if is_anonymous else author_name,
                    'author_type': author_type,
                    'is_anonymous': is_anonymous
                })
            except Exception as e:
                print(f"Error posting question: {e}")
        
        return redirect(url_for('social.ask_grandfriend'))
    
    return render_template('social/ask_grandfriend.html')


@social_bp.route('/ask-grandfriend/delete/<question_id>', methods=['POST'])
def delete_question_route(question_id):
    """Delete a question."""
    try:
        supabase = get_supabase()
        supabase.table('questions').delete().eq('id', question_id).execute()
    except Exception as e:
        print(f"Error deleting question: {e}")
    return redirect(url_for('social.ask_grandfriend'))
