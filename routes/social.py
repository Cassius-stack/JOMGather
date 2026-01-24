"""
Social routes - Social features, Chat, AskAGrandfriend
Now using Supabase for database
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from utils.supabase_db import get_supabase, fetch_all, fetch_one, insert
from utils.auth_middleware import login_required
import traceback

social_bp = Blueprint('social', __name__)


def get_current_user_id():
    """Get current user ID from session."""
    return session.get('user_id')


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

@social_bp.route('/search-results')
def search_results_page():
    """Full search results page."""
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('index'))
        
    currentUser = get_current_user_id()
    
    # 1. Search Users
    users = []
    try:
        supabase = get_supabase()
        response = supabase.table('users').select('user_id, username, user_type').ilike('username', f'%{query}%').neq('user_id', currentUser).execute()
        
        # Check friendship status for each
        for user in response.data:
            status = 'none'
            # Check sent
            sent = supabase.table('friendships').select('status').eq('user_id_1', currentUser).eq('user_id_2', user['user_id']).execute()
            if sent.data:
                status = sent.data[0]['status']
            else:
                # Check received
                rec = supabase.table('friendships').select('status').eq('user_id_1', user['user_id']).eq('user_id_2', currentUser).execute()
                if rec.data:
                    status = 'received' if rec.data[0]['status'] == 'pending' else 'accepted'
            
            users.append({
                'username': user['username'],
                'user_type': user['user_type'],
                'friendship_status': status
            })
    except Exception as e:
        print(f"Search users error: {e}")

    # 2. Search Activities
    from routes.activities import search_activities_logic
    activities = search_activities_logic(query)
    
    return render_template('social/search_results.html', query=query, users=users, activities=activities)

# === FRIEND REQUEST ENDPOINTS ===

@social_bp.route('/api/search')
@login_required
def search_users():
    """Search for users by username."""
    try:
        query = request.args.get('q', '').strip()
        current_user_id = get_current_user_id()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        supabase = get_supabase()
        # Search users logic
        # Note: 'ilike' might not be supported in all client versions or table settings. 
        # Checking robust implementation.
        
        # 1. Fetch potential matches
        response = supabase.table('users').select('user_id, username, user_type').ilike('username', f'%{query}%').neq('user_id', current_user_id).limit(10).execute()
        
        results = []
        if response.data:
            searched_users = response.data
            
            # Optimization: Fetch all relevant friendships in one go if possible, but loop is safer for prototype
            for user in searched_users:
                # Check friendship status
                status = 'none'
                
                # Check sent
                sent = supabase.table('friendships').select('status').eq('user_id_1', current_user_id).eq('user_id_2', user['user_id']).execute()
                if sent.data:
                    status = sent.data[0]['status'] 
                else:
                    # Check received
                    received = supabase.table('friendships').select('status').eq('user_id_1', user['user_id']).eq('user_id_2', current_user_id).execute()
                    if received.data:
                        status = 'received' if received.data[0]['status'] == 'pending' else 'accepted'
                
                results.append({
                    'id': user['user_id'],
                    'username': user['username'],
                    'type': user['user_type'],
                    'friendship_status': status
                })
            
        return jsonify(results)
    except Exception as e:
        print(f"Search API Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/friend-request', methods=['POST'])
def send_friend_request():
    """Send a friend request."""
    try:
        current_user_id = get_current_user_id()
        target_id = request.json.get('target_id')
        
        if not target_id:
            return jsonify({'error': 'Missing target_id'}), 400
            
        supabase = get_supabase()
        # Check existing
        existing = supabase.table('friendships').select('*').or_(
            f"and(user_id_1.eq.{current_user_id},user_id_2.eq.{target_id}),and(user_id_1.eq.{target_id},user_id_2.eq.{current_user_id})"
        ).execute()
        
        if existing.data:
            return jsonify({'error': 'Request already exists or matched'}), 400
            
        # Insert
        insert('friendships', {
            'user_id_1': current_user_id,
            'user_id_2': target_id,
            'status': 'pending'
        })
        
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/friend-accept', methods=['POST'])
def accept_friend_request():
    """Accept a friend request."""
    try:
        current_user_id = get_current_user_id()
        requester_id = request.json.get('requester_id')
        
        supabase = get_supabase()
        # Update status to accepted
        # user_id_1 is requester, user_id_2 is current_user
        supabase.table('friendships').update({'status': 'accepted'}).eq('user_id_1', requester_id).eq('user_id_2', current_user_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/contacts')
def get_contacts():
    """Get accepted friends."""
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get friendships where status is accepted and involves current user
        # Note: Supabase OR with AND logic is tricky in URL params, doing 2 queries for simplicity
        
        friends = []
        
        # 1. Where I am user_1 (I requested, they accepted)
        sent_accepted = supabase.table('friendships').select('user_id_2').eq('user_id_1', current_user_id).eq('status', 'accepted').execute()
        for item in sent_accepted.data:
            friends.append(item['user_id_2'])
            
        # 2. Where I am user_2 (They requested, I accepted)
        received_accepted = supabase.table('friendships').select('user_id_1').eq('user_id_2', current_user_id).eq('status', 'accepted').execute()
        for item in received_accepted.data:
            friends.append(item['user_id_1'])
            
        if not friends:
            return jsonify([])
            
        # Fetch user details for these IDs
        result = []
        for friend_id in friends:
            user_data = fetch_one('users', user_id=friend_id)
            if user_data:
                # Get last message
                last_msg = None
                try:
                    msg_res = supabase.table('messages').select('*').or_(
                        f"and(sender_id.eq.{current_user_id},receiver_id.eq.{friend_id}),and(sender_id.eq.{friend_id},receiver_id.eq.{current_user_id})"
                    ).order('sent_at', desc=True).limit(1).execute()
                    if msg_res.data:
                        last_msg = msg_res.data[0]
                except:
                    pass
                
                preview = ''
                if last_msg:
                    prefix = 'You: ' if last_msg['sender_id'] == current_user_id else ''
                    preview = f"{prefix}{last_msg['content'][:30]}"
                
                result.append({
                    'id': friend_id,
                    'name': user_data['username'],
                    'lastMessage': preview,
                    'status': 'Active now' # TODO: Real status
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
