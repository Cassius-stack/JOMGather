"""
Social routes - Social features, Chat, AskAGrandfriend
Now using Supabase for database
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import os
import tempfile
from utils.supabase_db import get_supabase, fetch_all, fetch_one, insert, retry_query
from utils.auth_middleware import login_required
import traceback
import os
import uuid
from werkzeug.utils import secure_filename
from utils.deepseek_client import generate_rag_response, generate_starter_prompts

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'social')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav'}

def validate_media_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_media_type(filename):
    if '.' not in filename: return None
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return 'image'
    elif ext in ['mp4', 'mov', 'webm']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg']:
        return 'audio'
    return None

social_bp = Blueprint('social', __name__)


@social_bp.route('/api/savvy-assist', methods=['POST'])
@login_required
def savvy_assist():
    """AI Navigation Assistant using DeepSeek."""
    data = request.get_json()
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    current_uid = get_current_user_id()
    
    # 1. Fetch friends for context
    try:
        supabase = get_supabase()
        friendships = fetch_all('friendships', status='accepted')
        friend_ids = []
        for f in friendships:
            if f['user_id_1'] == current_uid:
                friend_ids.append(f['user_id_2'])
            elif f['user_id_2'] == current_uid:
                friend_ids.append(f['user_id_1'])
                
        friends_context = []
        if friend_ids:
            all_users = fetch_all('users')
            for u in all_users:
                if u['user_id'] in friend_ids:
                    friends_context.append({'user_id': u['user_id'], 'username': u['username']})
        
        # 2. Call DeepSeek
        from utils.deepseek_client import determine_navigation_intent
        user_context = {
            'user_id': current_uid,
            'friends': friends_context
        }
        
        result = determine_navigation_intent(query, user_context)
        
        # 3. Process result - handle "chat" action specially
        if result.get('action') == 'chat' and result.get('target'):
            # Convert target to a URL that the frontend can handle
            result['target'] = url_for('social.social_hub', chat_with=result['target'])
        
        return jsonify(result)
    except Exception as e:
        print(f"Savvy Assist Error: {e}")
        return jsonify({'action': 'message', 'response': "I'm sorry, I'm having a little trouble thinking right now. Could you try again?"})


@social_bp.route('/api/savvy-transcribe', methods=['POST'])
@login_required
def savvy_transcribe():
    """Transcribe audio for Savvy Assist using Gemini."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Create a temporary file to save the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        # Call Gemini for transcription
        from utils.gemini_client import transcribe_audio
        text = transcribe_audio(tmp_path)

        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        if text:
            return jsonify({'text': text})
        else:
            return jsonify({'error': 'Could not transcribe audio'}), 500

    except Exception as e:
        print(f"Savvy Transcription Route Error: {e}")
        return jsonify({'error': str(e)}), 500


def get_current_user_id():
    """Get current user ID from session."""
    return session.get('user_id')


@social_bp.route('/')
def social_hub():
    """Main social/chat hub."""
    return render_template('social/social_hub.html')


@social_bp.route('/friends')
@login_required
def friends_list():
    """The 'See All Friends' page with search and status."""
    current_uid = get_current_user_id()
    search_q = request.args.get('q', '').lower().strip()
    
    supabase = get_supabase()
    
    # 1. Fetch friend IDs
    friendships = fetch_all('friendships', status='accepted')
    friend_ids = []
    for f in friendships:
        if f['user_id_1'] == current_uid:
            friend_ids.append(f['user_id_2'])
        elif f['user_id_2'] == current_uid:
            friend_ids.append(f['user_id_1'])
            
    if not friend_ids:
        return render_template('social/friends_list.html', friends=[], search_q=search_q)

    # 2. Fetch friend details
    all_users = fetch_all('users')
    friends = []
    import datetime
    
    def check_online(u):
        last_seen = u.get('last_seen')
        if not last_seen: return False
        try:
            five_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat()
            return last_seen > five_mins_ago
        except: return False

    for u in all_users:
        if u['user_id'] in friend_ids:
            if search_q and search_q not in u['username'].lower():
                continue
            
            u['is_online'] = check_online(u)
            friends.append(u)
            
    # Sort by online status then username
    friends.sort(key=lambda x: (not x['is_online'], x['username']))
    
    return render_template('social/friends_list.html', friends=friends, search_q=search_q)

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
        response = supabase.table('users').select('user_id, username, user_type').ilike('username', f'%{query}%').neq('user_id', currentUser).neq('is_deleted', True).execute()
        
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
        response = supabase.table('users').select('user_id, username, user_type').ilike('username', f'%{query}%').neq('user_id', current_user_id).neq('is_deleted', True).limit(10).execute()
        
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
        
        # Ensure target_id is an integer
        try:
            target_id = int(target_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid target_id'}), 400
            
        supabase = get_supabase()
        # Check existing
        existing = supabase.table('friendships').select('*').or_(
            f"and(user_id_1.eq.{current_user_id},user_id_2.eq.{target_id}),and(user_id_1.eq.{target_id},user_id_2.eq.{current_user_id})"
        ).execute()
        
        if existing.data:
            return jsonify({'error': 'Request already exists or matched'}), 400
            
        # Insert friendship
        insert('friendships', {
            'user_id_1': current_user_id,
            'user_id_2': target_id,
            'status': 'pending'
        })

        # Insert notification — store requester's user_id in link for direct accept/reject
        insert('notifications', {
            'user_id': target_id,
            'type': 'friend_request',
            'message': f"{session.get('username')} sent you a friend request!",
            'link': str(current_user_id),
            'is_read': False
        })
        
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/friend-accept', methods=['POST'])
def accept_friend_request():
    """Accept a friend request. Idempotent — safe to call multiple times."""
    try:
        current_user_id = get_current_user_id()
        requester_id = request.json.get('requester_id')
        
        if not requester_id:
            return jsonify({'error': 'Missing requester_id'}), 400
        
        # Ensure requester_id is an integer
        try:
            requester_id = int(requester_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid requester_id'}), 400
            
        supabase = get_supabase()
        
        # Check if friendship exists and its current status
        existing = supabase.table('friendships').select('*').eq('user_id_1', requester_id).eq('user_id_2', current_user_id).execute()
        
        if existing.data:
            if existing.data[0]['status'] == 'accepted':
                # Already friends — idempotent, just clean up notification
                pass
            else:
                # Update status to accepted
                supabase.table('friendships').update({'status': 'accepted'}).eq('user_id_1', requester_id).eq('user_id_2', current_user_id).execute()
        else:
            # No friendship record found — might have been deleted or wrong direction
            return jsonify({'error': 'Friend request not found'}), 404
        
        # Clear the specific notification for this friend request
        try:
            msg_frag = f"sent you a friend request!"
            supabase.table('notifications').delete().eq('user_id', current_user_id).ilike('message', f'%{msg_frag}%').execute()
        except:
            pass
            
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/friend-reject', methods=['POST'])
def reject_friend_request():
    """Reject a friend request."""
    try:
        current_user_id = get_current_user_id()
        requester_id = request.json.get('requester_id')
        
        if not requester_id:
            return jsonify({'error': 'Missing requester_id'}), 400
            
        supabase = get_supabase()
        # Delete the pending friendship record
        supabase.table('friendships').delete().eq('user_id_1', requester_id).eq('user_id_2', current_user_id).eq('status', 'pending').execute()
        
        # Clear notification
        try:
            msg_frag = f"sent you a friend request!"
            supabase.table('notifications').delete().eq('user_id', current_user_id).ilike('message', f'%{msg_frag}%').execute()
        except:
            pass
            
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@social_bp.route('/api/contacts')
def get_contacts():
    """Get accepted friends, sorted by most recent message."""
    import time
    
    def query_with_retry(query_func, max_retries=3):
        """Execute a query with retry on network errors."""
        for attempt in range(max_retries):
            try:
                return query_func()
            except Exception as e:
                error_str = str(e).lower()
                retryable = any(kw in error_str for kw in [
                    "10035", "timeout", "transport", "read",
                    "connection", "reset", "502", "503", "504",
                    "temporarily", "unavailable", "eof"
                ])
                if retryable:
                    print(f"[Contacts API] Retry {attempt+1}/{max_retries}: {e}")
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise
        return None
    
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get friendships where status is accepted and involves current user
        friends = []
        
        # 1. Where I am user_1 (I requested, they accepted)
        sent_accepted = query_with_retry(
            lambda: supabase.table('friendships').select('user_id_2').eq('user_id_1', current_user_id).eq('status', 'accepted').execute()
        )
        if sent_accepted:
            for item in sent_accepted.data:
                friends.append(item['user_id_2'])
            
        # 2. Where I am user_2 (They requested, I accepted)
        received_accepted = query_with_retry(
            lambda: supabase.table('friendships').select('user_id_1').eq('user_id_2', current_user_id).eq('status', 'accepted').execute()
        )
        if received_accepted:
            for item in received_accepted.data:
                friends.append(item['user_id_1'])
            
        if not friends:
            return jsonify([])
        
        # Helper: Check if user is online (active in last 5 mins)
        import datetime
        def is_online(user_data):
            last_seen = user_data.get('last_seen')
            if not last_seen:
                return False
            try:
                five_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat()
                return last_seen > five_mins_ago
            except:
                return False
            
        # Fetch user details for these IDs
        result = []
        for friend_id in friends:
            try:
                user_data = fetch_one('users', user_id=friend_id)
                if not user_data:
                    continue
                    
                # Get messages for preview and sorting
                last_msg = None
                last_msg_time = None
                try:
                    # 1. Get the absolute last message for the preview text
                    msg_res = supabase.table('messages').select('*').or_(
                        f"and(sender_id.eq.{current_user_id},receiver_id.eq.{friend_id}),and(sender_id.eq.{friend_id},receiver_id.eq.{current_user_id})"
                    ).order('sent_at', desc=True).limit(1).execute()
                    if msg_res.data:
                        last_msg = msg_res.data[0]
                    
                    # 2. Get the last NON-CYBER message for sorting
                    # This ensures automated challenges don't jump the contact to the top
                    real_msg_res = supabase.table('messages').select('sent_at').or_(
                        f"and(sender_id.eq.{current_user_id},receiver_id.eq.{friend_id}),and(sender_id.eq.{friend_id},receiver_id.eq.{current_user_id})"
                    ).neq('content', '!cyber').order('sent_at', desc=True).limit(1).execute()
                    
                    if real_msg_res.data:
                        last_msg_time = real_msg_res.data[0].get('sent_at')
                except Exception as e:
                    print(f"[Contacts] Error fetching last message for {friend_id}: {e}")
                
                preview = ''
                if last_msg:
                    prefix = 'You: ' if last_msg['sender_id'] == current_user_id else ''
                    content = last_msg['content']
                    if content and content.startswith('{'):
                        try:
                            import json
                            parsed_data = json.loads(content)
                            if parsed_data.get('type') == 'call':
                                call_type = parsed_data.get('call_type', 'voice')
                                content = f"📹 Video call" if call_type == 'video' else f"📞 Voice call"
                            elif parsed_data.get('type') == 'voice':
                                content = "🎙️ Voice message"
                        except:
                            pass
                    
                    stripped_content = content.strip().lower() if content else ''
                    if 'Slice of Life Invite' in content:
                        preview = f"{prefix}🎨 Slice of Life Invite"
                    elif stripped_content == '!cyber':
                        preview = f"{prefix}🎮 Cyber Challenge!"
                    else:
                        preview = f"{prefix}{content[:30]}"
                
                # Determine online status from last_seen
                status = 'Active' if is_online(user_data) else 'Offline'
                
                # Count unread messages from this friend
                unread_count = 0
                try:
                    unread_res = supabase.table('messages').select('message_id', count='exact').eq('sender_id', friend_id).eq('receiver_id', current_user_id).eq('read', False).execute()
                    unread_count = unread_res.count or 0
                except:
                    pass
                
                result.append({
                    'id': friend_id,
                    'name': user_data['username'],
                    'type': user_data.get('user_type', 'youth'),
                    'lastMessage': preview,
                    'status': status,
                    'lastMessageTime': last_msg_time,
                    'unreadCount': unread_count
                })
            except Exception as e:
                print(f"[Contacts] Skipping friend {friend_id} due to error: {e}")
                continue
        
        # Sort by last message time (most recent first), new friends (no messages) at top
        result.sort(key=lambda x: x.get('lastMessageTime') or '9999-99-99', reverse=True)
                
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_contacts: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/messages/<int:contact_id>/read', methods=['POST'])
def mark_messages_read(contact_id):
    """Mark all messages from a contact as read."""
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Mark all unread messages from this contact as read
        supabase.table('messages').update({'read': True}).eq('sender_id', contact_id).eq('receiver_id', current_user_id).eq('read', False).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error marking messages as read: {e}")
        return jsonify({'error': str(e)}), 500


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@social_bp.route('/api/upload_image', methods=['POST'])
def upload_chat_image():
    """Upload an image for chat (Strictly images only)."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            import os
            from werkzeug.utils import secure_filename
            
            # Server-side validation for images only
            if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({'error': 'Only image files (jpg, jpeg, png, gif) are allowed.'}), 400

            # Ensure upload directory exists
            upload_folder = os.path.join('static', 'uploads', 'chat')
            os.makedirs(upload_folder, exist_ok=True)
            
            filename = secure_filename(file.filename)
            # Add timestamp to prevent duplicates
            import time
            timestamp = int(time.time())
            filename = f"{timestamp}_{filename}"
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Return web-accessible URL
            url = f"/static/uploads/chat/{filename}"
            return jsonify({'url': url})
            
    except Exception as e:
        print(f"Error uploading image: {e}")
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/upload_audio', methods=['POST'])
def upload_chat_audio():
    """Upload an audio file for voice messages."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            import os
            import time
            
            # Ensure upload directory exists
            upload_folder = os.path.join('static', 'uploads', 'audio')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generate unique filename with timestamp
            timestamp = int(time.time() * 1000)
            filename = f"voice_{timestamp}.webm"
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Return web-accessible URL
            url = f"/static/uploads/audio/{filename}"
            return jsonify({'url': url})
            
    except Exception as e:
        print(f"Error uploading audio: {e}")
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
        
        # Get reactions for these messages
        message_ids = [m['message_id'] for m in messages]
        reactions_map = {}
        challenge_map = {}
        
        if message_ids:
            # 1. Fetch reactions
            try:
                reactions_res = supabase.table('message_reactions').select('*').in_('message_id', message_ids).execute()
                for r in reactions_res.data:
                    mid = r['message_id']
                    emoji = r['emoji']
                    uid = r['user_id']
                    if mid not in reactions_map:
                        reactions_map[mid] = {}
                    if emoji not in reactions_map[mid]:
                        reactions_map[mid][emoji] = []
                    reactions_map[mid][emoji].append(uid)
            except Exception as re:
                print(f"Error fetching message reactions: {re}")

            # 2. Fetch cyber challenges
            try:
                challenges_res = supabase.table('cyber_challenges').select('*').in_('message_id', message_ids).execute()
                for c in challenges_res.data:
                    challenge_map[c['message_id']] = {
                        'challenge_id': c['challenge_id'],
                        'scenario_id': c['scenario_id']
                    }
            except Exception as ce:
                print(f"Error fetching cyber challenges: {ce}")
        
        return jsonify([{
            'id': m['message_id'],
            'type': 'sent' if m['sender_id'] == current_user_id else 'received',
            'text': m['content'],
            'sent_at': m['sent_at'],
            'read': m.get('read', False),
            'image_url': m.get('image_url'),
            'is_cyber_challenge': m['message_id'] in challenge_map,
            'challenge_id': challenge_map.get(m['message_id'], {}).get('challenge_id'),
            'scenario_id': challenge_map.get(m['message_id'], {}).get('scenario_id'),
            'reactions': reactions_map.get(m['message_id'], {})
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

def get_user_rank(coins):
    """Determine the user's AskAGrandfriend rank based on earned forum coins."""
    coins = coins or 0
    if coins >= 400:
        return {'tier': 6, 'name': 'Legendary Bridge-Builder', 'css_class': 'rank-tier-6'}
    elif coins >= 200:
        return {'tier': 5, 'name': 'Wisdom Keeper', 'css_class': 'rank-tier-5'}
    elif coins >= 100:
        return {'tier': 4, 'name': 'Trusted Guide', 'css_class': 'rank-tier-4'}
    elif coins >= 40:
        return {'tier': 3, 'name': 'Kindred Spirit', 'css_class': 'rank-tier-3'}
    elif coins >= 20:
        return {'tier': 2, 'name': 'The Icebreaker', 'css_class': 'rank-tier-2'}
    else:
        return {'tier': 1, 'name': 'Friendly Neighbor', 'css_class': 'rank-tier-1'}


@social_bp.route('/ask-grandfriend')
def ask_grandfriend():
    """AskAGrandfriend forum."""
    questions = []
    all_raw_replies = []
    sort_by = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')
    unanswered_only = request.args.get('unanswered', 'false').lower() == 'true'
    is_desc = (order == 'desc')

    try:
        supabase = get_supabase()
        
        # Build query based on sort preference
        query = supabase.table('questions').select('*')
        if sort_by == 'likes':
            query = query.order('likes', desc=is_desc).order('created_at', desc=True)
        else:
            query = query.order('created_at', desc=is_desc)
            
        try:
            q_res = query.execute()
        except Exception:
            # Fallback: likes column may not exist yet
            q_res = supabase.table('questions').select('*').order('created_at', desc=is_desc).execute()
        questions = q_res.data if q_res.data else []
        # Ensure every question has a likes count
        for q in questions:
            if q.get('likes') is None:
                q['likes'] = 0
        
        # Fetch Replies
        r_res = supabase.table('replies').select('*').order('created_at').execute() 
        all_raw_replies = r_res.data if r_res.data else []
        
        # Organize Nesting
        reply_map = {r['reply_id']: r for r in all_raw_replies}
        for r in all_raw_replies: r['sub_replies'] = [] # Init
        
        # Calculate forum coins for all users to determine ranks efficiently
        user_coins = {}
        for r in all_raw_replies:
            uid = r.get('user_id')
            if uid:
                # Add coins awarded from replies
                user_coins[uid] = user_coins.get(uid, 0) + (r.get('coins_awarded') or 0)
                
        # Inject ranks into all replies
        for r in all_raw_replies:
            ruid = r.get('user_id')
            r['rank'] = get_user_rank(user_coins.get(ruid, 0))
        
        top_level_replies = []
        for r in all_raw_replies:
            pid = r.get('parent_reply_id')
            if pid and pid in reply_map:
                reply_map[pid]['sub_replies'].append(r)
            elif not pid:
                top_level_replies.append(r)
        
        # Attach to questions (Top Level Only)
        for q in questions:
            # Inject rank into question
            quid = q.get('user_id')
            q['rank'] = get_user_rank(user_coins.get(quid, 0))
            
            q['replies'] = [r for r in top_level_replies if r['question_id'] == q['id']]
            # Sort by coins desc
            q['replies'].sort(key=lambda x: x.get('coins_awarded', 0), reverse=True)
            # Count total (including subs)? The current UI shows "X Replies". 
            # q.replies_count is usually just top level or total? 
            # Typically total. Let's count properly.
            total_count = 0
            for r in q['replies']:
                total_count += 1 + len(r['sub_replies'])
            q['replies_count'] = total_count
            
        # Filter unanswered if requested
        if unanswered_only:
            questions = [q for q in questions if q['replies_count'] == 0]
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    current_user_id = get_current_user_id()
    current_username = "Jeremy Khoo" # Default fallback
    if current_user_id:
        try:
            u = fetch_one('users', user_id=current_user_id)
            if u: current_username = u.get('username')
        except: pass
    
    # Build history: collect unique users who have posted questions or replies
    history_users = []
    try:
        supabase = get_supabase()
        user_ids_set = set()
        
        # Collect user_ids from questions and replies
        for q in questions:
            uid = q.get('user_id')
            if uid and uid != current_user_id:
                user_ids_set.add(uid)
        for r in all_raw_replies:
            uid = r.get('user_id')
            if uid and uid != current_user_id:
                user_ids_set.add(uid)
        
        if user_ids_set:
            # Fetch user profiles
            user_ids_list = list(user_ids_set)
            users_res = supabase.table('users').select('user_id, username').in_('user_id', user_ids_list).execute()
            users_data = {u['user_id']: u for u in (users_res.data or [])}
            
            # Fetch friendships involving current user
            friend_statuses = {}
            if current_user_id:
                fr_res = supabase.table('friendships').select('*').or_(
                    f"user_id_1.eq.{current_user_id},user_id_2.eq.{current_user_id}"
                ).execute()
                for f in (fr_res.data or []):
                    other_id = f['user_id_2'] if f['user_id_1'] == current_user_id else f['user_id_1']
                    friend_statuses[other_id] = f['status']  # 'pending' or 'accepted'
            
            for uid in user_ids_list:
                udata = users_data.get(uid, {})
                friendship = friend_statuses.get(uid)
                history_users.append({
                    'user_id': uid,
                    'username': udata.get('username', 'Unknown'),
                    'profile_picture': udata.get('profile_picture'),
                    'friendship_status': friendship  # None, 'pending', or 'accepted'
                })
    except Exception as e:
        print(f"Error building history: {e}")
        
    # Determine which questions the current user has liked (from liked_by arrays)
    liked_question_ids = set()
    if current_user_id:
        uid_str = str(current_user_id)
        for q in questions:
            liked_by = q.get('liked_by') or []
            if liked_by:
                print(f"DEBUG LIKE: q.id={q['id']} liked_by={liked_by} type={type(liked_by)} current_user_id={current_user_id} type={type(current_user_id)}")
            if current_user_id in liked_by or uid_str in [str(x) for x in liked_by]:
                liked_question_ids.add(q['id'])
        print(f"DEBUG LIKE: liked_question_ids={liked_question_ids}")

    user_type = session.get('user_type', 'youth')
    return render_template('social/ask_grandfriend.html', 
                           questions=questions, 
                           current_user_id=current_user_id, 
                           current_username=current_username, 
                           history_users=history_users, 
                           user_type=user_type, 
                           liked_question_ids=liked_question_ids,
                           current_sort=sort_by,
                           current_order=order,
                           current_unanswered=unanswered_only)

@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        user_id = get_current_user_id()
        if not user_id:
            from flask import flash
            flash("Please log in to ask a question.", "warning")
            return redirect(url_for('auth.login'))
        
        # Role check: only students (youth) can post questions
        current_type = session.get('user_type', 'youth')
        if current_type == 'senior':
            from flask import flash
            flash("Grandparents can reply to questions but cannot post new ones.", "warning")
            return redirect(url_for('social.ask_grandfriend'))
            
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'tech')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        
        # Fetch actual user details
        try:
            user_data = fetch_one('users', user_id=user_id)
            if not user_data:
                from flask import flash
                flash("User session invalid. Please log in again.", "error")
                return redirect(url_for('auth.login'))
                
            author_name = user_data.get('username', 'Unknown')
            db_type = str(user_data.get('user_type', 'youth')).lower()
            # Map 'youth'/'senior' to 'student'/'grandparent' for questions table constraint
            if db_type == 'senior':
                author_type = 'grandparent'
            elif db_type == 'youth':
                author_type = 'student'
            else:
                author_type = 'student' # default fallback
        except Exception as e:
            print(f"Error fetching user details: {e}")
            author_name = "User"
            author_type = "student"

        # Handle File Upload
        media_url = None
        media_type = None
        media_file = request.files.get('media')
        
        if media_file and media_file.filename:
            if validate_media_file(media_file.filename):
                filename = secure_filename(media_file.filename)
                unique_name = f"{uuid.uuid4()}_{filename}"
                
                # ensure directory exists
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                    
                local_path = os.path.join(UPLOAD_FOLDER, unique_name)
                media_file.save(local_path)
                
                # relative URL for static
                # Note: need to fix path slashes for URL
                media_url = url_for('static', filename=f'uploads/social/{unique_name}')
                media_type = get_media_type(filename)
            else:
                from flask import flash
                flash("Invalid file type. Allowed: Image, Video, Audio.", "warning")
                return redirect(url_for('social.ask_grandfriend'))

        if title:
            success = False
            try:
                # Try inserting with user_id (New Schema)
                data = {
                    'title': title,
                    'content': content,
                    'category': category,
                    'author_name': 'Anonymous' if is_anonymous else author_name,
                    'author_type': author_type,
                    'is_anonymous': is_anonymous,
                    'user_id': user_id
                }
                if media_url:
                    data['media_url'] = media_url
                    data['media_type'] = media_type
                    
                insert('questions', data)
                success = True
            except Exception as e:
                print(f"Error posting with user_id: {e}")
                # Fallback to Old Schema (no user_id column)
                try:
                     # try original fallback without media first if column missing?
                     # actually lets assume user ran schema update
                    data = {
                        'title': title,
                        'content': content,
                        'category': category,
                        'author_name': 'Anonymous' if is_anonymous else author_name,
                        'author_type': author_type,
                        'is_anonymous': is_anonymous
                    }
                    if media_url:
                        data['media_url'] = media_url
                        data['media_type'] = media_type
                        
                    insert('questions', data)
                    success = True
                except Exception as e2:
                    print(f"Error posting fallback: {e2}")
                    from flask import flash
                    flash(f"Error posting question: {str(e2)}", "error")
            
            if success:
                from flask import flash
                flash("Question posted successfully!", "success")
        
        return redirect(url_for('social.ask_grandfriend'))
    
    return render_template('social/ask_grandfriend.html')


@social_bp.route('/ask-grandfriend/react/<reply_id>/<reaction_type>', methods=['POST'])
def react_to_reply_route(reply_id, reaction_type):
    """React to a reply (favourite, love, like). Only OP can do this."""
    user_id = get_current_user_id()
    if not user_id: return redirect(url_for('auth.login'))
    
    allowed_reactions = {
        'favourite': 20,
        'love': 10,
        'like': 5,
        'none': 0
    }
    
    if reaction_type not in allowed_reactions:
        return redirect(url_for('social.ask_grandfriend'))

    try:
        supabase = get_supabase()
        
        # 1. Fetch Reply and Question to verify ownership
        # We need question_id to check who owns the question
        reply_res = supabase.table('replies').select('*, question_id').eq('reply_id', reply_id).execute()
        if not reply_res.data: return redirect(url_for('social.ask_grandfriend'))
        reply = reply_res.data[0]
        question_id = reply['question_id']
        
        q_res = supabase.table('questions').select('user_id').eq('id', question_id).execute()
        if not q_res.data: return redirect(url_for('social.ask_grandfriend'))
        question = q_res.data[0]
        
        # Verify OP Check
        # Ensure we compare strings properly if UUIDs
        if str(question.get('user_id')) != str(user_id):
            from flask import flash
            flash("Only the question author can react.", "error")
            return redirect(url_for('social.ask_grandfriend'))

        # 2. Calculate Coin Diff
        old_coins = reply.get('coins_awarded', 0)
        new_coins = allowed_reactions[reaction_type]
        coin_diff = new_coins - old_coins
        
        # 3. Update Reply
        new_reaction = None if reaction_type == 'none' else reaction_type
        supabase.table('replies').update({
            'reaction': new_reaction,
            'coins_awarded': new_coins
        }).eq('reply_id', reply_id).execute()
        
        # 4. Award/Revoke Coins from Replier
        replier_id = reply.get('user_id')
        if replier_id and coin_diff != 0:
            # Check if user exists in coins table
            # This requires 'coins' table to be setup for the user. 
            # If not, we might need to insert.
            # For prototype, we attempt update.
            try:
                # Fetch current coins
                c_res = supabase.table('coins').select('total_coins').eq('user_id', replier_id).execute()
                if c_res.data:
                    curr = c_res.data[0]['total_coins']
                    supabase.table('coins').update({'total_coins': curr + coin_diff}).eq('user_id', replier_id).execute()
                else:
                    # Insert
                    supabase.table('coins').insert({'user_id': replier_id, 'total_coins': coin_diff}).execute()
            except Exception as e:
                print(f"Coin update failed: {e}")

        from flask import flash
        flash(f"Reaction updated! Awarded {new_coins} coins.", "success")
        
    except Exception as e:
        print(f"Reaction Error: {e}")
        from flask import flash
        flash(f"Error reacting: {e}", "error")

    return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/ask-grandfriend/reply/<question_id>', methods=['POST'])
def post_reply(question_id):
    """Post a reply to a question."""
    user_id = get_current_user_id()
    if not user_id:
        from flask import flash
        flash("Please log in to reply.", "warning")
        return redirect(url_for('auth.login'))

    content = request.form.get('content', '').strip()
    parent_reply_id = request.form.get('parent_reply_id')
    
    if not content:
        return redirect(url_for('social.ask_grandfriend'))

    # Role check: can only reply to opposite type's questions
    current_type = session.get('user_type', 'youth')
    try:
        q_data = fetch_one('questions', id=question_id)
        if q_data:
            q_author_type = q_data.get('author_type', '')
            # Students can only reply to grandparent posts, grandparents to student posts
            # EXCEPTION: Original Poster can always reply to their own post
            is_op = str(q_data.get('user_id', '')) == str(user_id)
            
            if not is_op:
                if (current_type == 'youth' and q_author_type == 'student') or \
                   (current_type == 'senior' and q_author_type == 'grandparent'):
                    from flask import flash
                    flash("You can only reply to posts from the other group.", "warning")
                    return redirect(url_for('social.ask_grandfriend'))
    except Exception as e:
        print(f"Error checking question author type: {e}")

    # Determine Author
    try:
        user_data = fetch_one('users', user_id=user_id)
        author_name = user_data.get('username', 'User') if user_data else 'User'
        
        db_type = str(user_data.get('user_type', 'youth')).lower() if user_data else 'youth'
        if db_type == 'senior': author_type = 'grandparent'
        elif db_type == 'youth': author_type = 'student'
        else: author_type = 'student'
    except:
        author_name = "User"
        author_type = "student"

    # Handle File Upload
    media_url = None
    media_type = None
    media_file = request.files.get('media')
    
    if media_file and media_file.filename:
        if validate_media_file(media_file.filename):
            filename = secure_filename(media_file.filename)
            unique_name = f"{uuid.uuid4()}_{filename}"
            
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
                
            local_path = os.path.join(UPLOAD_FOLDER, unique_name)
            media_file.save(local_path)
            
            media_url = url_for('static', filename=f'uploads/social/{unique_name}')
            media_type = get_media_type(filename)
        else:
            from flask import flash
            flash("Invalid file type.", "warning")
            return redirect(url_for('social.ask_grandfriend'))

    try:
        data = {
            'question_id': question_id,
            'user_id': user_id,
            'content': content,
            'author_name': author_name,
            'author_type': author_type
        }
        if media_url:
            data['media_url'] = media_url
            data['media_type'] = media_type

        if parent_reply_id:
            data['parent_reply_id'] = parent_reply_id
            
        insert('replies', data)
        from flask import flash
        flash("Reply posted!", "success")
    except Exception as e:
        print(f"Error posting reply: {e}")
        from flask import flash
        flash(f"Error posting reply: {e}", "error")

    return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/ask-grandfriend/reply/delete/<reply_id>', methods=['POST'])
def delete_reply_route(reply_id):
    """Delete a reply (Only OP or Author)."""
    user_id = get_current_user_id()
    if not user_id: return redirect(url_for('auth.login'))
    
    try:
        supabase = get_supabase()
        # Fetch reply to check ownership and question ownership
        res = supabase.table('replies').select('*, questions(user_id)').eq('reply_id', reply_id).execute()
        if not res.data: return redirect(url_for('social.ask_grandfriend'))
        reply = res.data[0]
        
        # Check permissions:
        # 1. Reply Author
        # 2. Question Author (OP)
        # Note: join syntax `questions(user_id)` needs setup or simpler separate fetch. 
        # Supabase-py join can be tricky. Let's do separate fetch.
        
        q_res = supabase.table('questions').select('user_id').eq('id', reply['question_id']).execute()
        q_owner = str(q_res.data[0]['user_id']) if q_res.data else None
        
        reply_author = str(reply.get('user_id'))
        current = str(user_id)
        
        if current == reply_author or current == q_owner:
            supabase.table('replies').delete().eq('reply_id', reply_id).execute()
            from flask import flash
            flash("Reply deleted.", "success")
        else:
            from flask import flash
            flash("Unauthorized.", "error")
            
    except Exception as e:
        print(f"Delete error: {e}")
        
    return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/ask-grandfriend/profile/<int:user_id>')
def agf_profile(user_id):
    """AskAGrandfriend specific profile page showing forum stats."""
    current_user_id = get_current_user_id()
    if not current_user_id:
        from flask import flash
        flash("Please log in to view profiles.", "warning")
        return redirect(url_for('auth.login'))

    try:
        supabase = get_supabase()
        
        # 1. Fetch User Data
        u_res = supabase.table('users').select('user_id, username, profile_picture, user_type').eq('user_id', user_id).execute()
        if not u_res.data:
            from flask import flash
            flash("User not found.", "error")
            return redirect(url_for('social.ask_grandfriend'))
        
        profile_user = u_res.data[0]
        
        # 2. Calculate Stats
        stats = {
            'posts': 0,
            'replies': 0,
            'likes': 0,
            'coins': 0
        }
        
        # Fetch their questions
        q_res = supabase.table('questions').select('id, title, created_at, likes').eq('user_id', user_id).order('created_at', desc=True).execute()
        user_questions = q_res.data if q_res.data else []
        stats['posts'] = len(user_questions)
        stats['likes'] = sum(q.get('likes') or 0 for q in user_questions)
        
        # Fetch their replies
        r_res = supabase.table('replies').select('reply_id, content, created_at, coins_awarded').eq('user_id', user_id).order('created_at', desc=True).execute()
        user_replies = r_res.data if r_res.data else []
        stats['replies'] = len(user_replies)
        stats['coins'] = sum(r.get('coins_awarded') or 0 for r in user_replies)
        
        # Inject Rank
        profile_user['rank'] = get_user_rank(stats['coins'])
        
        # 3. Check Friendship Status
        friendship_status = 'none'
        if current_user_id != user_id:
            sent = supabase.table('friendships').select('status').eq('user_id_1', current_user_id).eq('user_id_2', user_id).execute()
            if sent.data:
                friendship_status = sent.data[0]['status'] # 'pending' or 'accepted'
            else:
                rec = supabase.table('friendships').select('status').eq('user_id_1', user_id).eq('user_id_2', current_user_id).execute()
                if rec.data:
                    friendship_status = 'received' if rec.data[0]['status'] == 'pending' else 'accepted'
                    
        return render_template('social/agf_profile.html', 
                               profile_user=profile_user, 
                               stats=stats, 
                               recent_questions=user_questions[:5],
                               recent_replies=user_replies[:5],
                               friendship_status=friendship_status,
                               current_user_id=current_user_id)
                               
    except Exception as e:
        print(f"Error fetching AGF profile: {e}")
        import traceback
        traceback.print_exc()
        from flask import flash
        flash("An error occurred loading the profile.", "error")
        return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/ask-grandfriend/delete/<question_id>', methods=['POST'])
def delete_question_route(question_id):
    """Delete a question."""
    try:
        supabase = get_supabase()
        supabase.table('questions').delete().eq('id', question_id).execute()
    except Exception as e:
        print(f"Error deleting question: {e}")
    return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/api/like-question', methods=['POST'])
def like_question():
    """Toggle like on a question. Uses liked_by JSONB array on questions table. Bypasses RLS."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    question_id = data.get('question_id')
    if not question_id:
        return jsonify({'error': 'Missing question_id'}), 400

    try:
        from supabase import create_client
        import os
        
        # Use Service Role Key to bypass RLS for this specific update
        url = os.environ.get("SUPABASE_URL")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if service_key:
            admin_supabase = create_client(url, service_key)
        else:
            # Fallback to standard client if no service key, though RLS might block
            print("LIKE DEBUG: WARNING - SUPABASE_SERVICE_ROLE_KEY not found. RLS might block this update.")
            admin_supabase = get_supabase()

        # Fetch the question's current state
        q = admin_supabase.table('questions').select('*').eq('id', question_id).execute()
        if not q.data:
            return jsonify({'error': 'Question not found'}), 404

        question = q.data[0]
        liked_by = question.get('liked_by') or []
        print(f"LIKE DEBUG [BEFORE]: question_id={question_id}, user_id={user_id}({type(user_id).__name__}), liked_by={liked_by}, likes={question.get('likes')}")
        
        # Check if 'liked_by' key exists in the response at all
        if 'liked_by' not in question:
            print(f"LIKE DEBUG: WARNING - 'liked_by' column NOT in question data! Available keys: {list(question.keys())}")
            current_likes = question.get('likes') or 0
            new_likes = current_likes + 1
            admin_supabase.table('questions').update({'likes': new_likes}).eq('id', question_id).execute()
            return jsonify({'liked': True, 'likes': new_likes})

        # Normalize: compare as strings to handle int/str mismatch
        uid_str = str(user_id)
        liked_by_str = [str(x) for x in liked_by]

        if uid_str in liked_by_str:
            # Unlike: remove user from liked_by
            liked_by = [x for x in liked_by if str(x) != uid_str]
            new_likes = len(liked_by)
            update_result = admin_supabase.table('questions').update({'likes': new_likes, 'liked_by': liked_by}).eq('id', question_id).execute()
            print(f"LIKE DEBUG [UNLIKE]: updated to liked_by={liked_by}, likes={new_likes}, result={update_result.data}")
            return jsonify({'liked': False, 'likes': new_likes})
        else:
            # Like: add user to liked_by
            liked_by.append(user_id)
            new_likes = len(liked_by)
            update_result = admin_supabase.table('questions').update({'likes': new_likes, 'liked_by': liked_by}).eq('id', question_id).execute()
            print(f"LIKE DEBUG [LIKE]: updated to liked_by={liked_by}, likes={new_likes}, result={update_result.data}")
            
            # Verify: re-read from DB
            verify = admin_supabase.table('questions').select('likes, liked_by').eq('id', question_id).execute()
            print(f"LIKE DEBUG [VERIFY]: DB now has: {verify.data}")
            
            return jsonify({'liked': True, 'likes': new_likes})

    except Exception as e:
        print(f"Like error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/cyber-challenge/<challenge_id>')
def get_cyber_challenge_status(challenge_id):
    """Get the status of a cyber challenge (who has answered, etc.)."""
    try:
        user_id = request.args.get('user', type=int)
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        supabase = get_supabase()
        
        # Handle both numeric and string challenge IDs
        if str(challenge_id).startswith('msg_'):
            # This is a fallback ID using message_id
            message_id = int(challenge_id.replace('msg_', ''))
            result = supabase.table('cyber_challenges').select('*').eq('message_id', message_id).execute()
        else:
            # Direct challenge_id lookup
            result = supabase.table('cyber_challenges').select('*').eq('challenge_id', int(challenge_id)).execute()
        
        if not result.data:
            return jsonify({'found': False, 'status': 'not_found'})
        
        challenge = result.data[0]
        
        # Determine if current user has answered
        if user_id == challenge['user1_id']:
            my_answer = challenge.get('user1_answer')
            partner_answer = challenge.get('user2_answer')
        elif user_id == challenge['user2_id']:
            my_answer = challenge.get('user2_answer')
            partner_answer = challenge.get('user1_answer')
        else:
            return jsonify({'found': False, 'error': 'User not part of this challenge'})
        
        return jsonify({
            'found': True,
            'challenge_id': challenge['challenge_id'],
            'scenario_id': challenge['scenario_id'],
            'status': challenge['status'],
            'my_answer': my_answer,
            'partner_answered': partner_answer is not None,
            'user1_id': challenge['user1_id'],
            'user2_id': challenge['user2_id'],
            'user1_answer': challenge.get('user1_answer'),
            'user2_answer': challenge.get('user2_answer')
        })
    except Exception as e:
        print(f"Error getting cyber challenge status: {e}")
        return jsonify({'found': False, 'error': str(e)}), 500

# -------------------------------------------------------------------------
# AI CHATBOT ROUTES
# -------------------------------------------------------------------------

@social_bp.route('/api/chatbot/query', methods=['POST'])
@login_required
def chatbot_query():
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # 1. Fetch recent Q&A for context (Naive RAG)
        # In a real app, use vector embeddings. Here, we just fetch recent text.
        supabase = get_supabase()
        
        # Fetch Questions
        q_res = supabase.table('questions') \
            .select('title, content, category, created_at') \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()
        q_rows = q_res.data if q_res else []
        
        # Fetch Replies (best answers)
        r_res = supabase.table('replies') \
            .select('content, created_at') \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()
        r_rows = r_res.data if r_res else []
        
        context_list = []
        for q in q_rows:
            context_list.append(f"Question ({q.get('category')}): {q.get('title')} - {q.get('content')}")
            
        for r in r_rows:
            context_list.append(f"Answer: {r['content']}")
            
        
        # 2. Generate Answer
        print(f"DEBUG: Generating answer for query: {query}")
        print(f"DEBUG: Context length: {len(context_list)}")
        answer = generate_rag_response(query, context_list)
        print(f"DEBUG: Answer generated: {answer[:50]}...")
        
        # Ensure answer is a string and strip weird chars
        safe_answer = str(answer).strip()
        print(f"DEBUG: Safe Answer: {repr(safe_answer)}")
        return jsonify({'answer': safe_answer})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/api/chatbot/prompts', methods=['GET'])
@login_required
def chatbot_prompts():
    try:
        # Fetch recent topics/categories
        supabase = get_supabase()
        res = supabase.table('questions') \
            .select('title, content, category, created_at') \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()
        rows = res.data if res else []
        
        # Extract topics and content for prompts
        recent_data = []
        for r in rows:
             recent_data.append({
                 'category': r.get('category'),
                 'title': r.get('title'),
                 'content': r.get('content')
             })
        
        prompts = generate_starter_prompts(recent_data)
        return jsonify({'prompts': prompts})
        
    except Exception as e:
        print(f"Prompts Error: {e}")
        return jsonify({'prompts': ["Tell me a story", "Advice needed", "Childhood memory"]})

@social_bp.route('/api/debug/trigger-challenges')
def debug_trigger_challenges():
    """Manual trigger for daily cyber challenges (for testing)."""
    try:
        from extensions import socketio
        from utils.scheduler import send_daily_cyber_challenges
        send_daily_cyber_challenges(socketio)
        return jsonify({'success': True, 'message': 'Daily challenges triggered.'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# NOTIFICATION MANAGEMENT API
# ============================================

@social_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    try:
        supabase = get_supabase()
        supabase.table('notifications').update({'is_read': True}).eq('user_id', session['user_id']).eq('is_read', False).execute()
        # Invalidate cache
        session.pop('_notif_cache_time', None)
        session.pop('_cached_notifs', None)
        session.pop('_cached_unread', None)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error marking all read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@social_bp.route('/api/notifications/<notif_id>', methods=['DELETE'])
@login_required
def delete_notification(notif_id):
    """Delete a single notification."""
    try:
        supabase = get_supabase()
        supabase.table('notifications').delete().eq('notification_id', notif_id).eq('user_id', session['user_id']).execute()
        # Invalidate cache
        session.pop('_notif_cache_time', None)
        session.pop('_cached_notifs', None)
        session.pop('_cached_unread', None)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@social_bp.route('/api/notifications/clear-all', methods=['DELETE'])
@login_required
def clear_all_notifications():
    """Delete ALL notifications for the current user."""
    try:
        supabase = get_supabase()
        supabase.table('notifications').delete().eq('user_id', session['user_id']).execute()
        # Invalidate cache
        session.pop('_notif_cache_time', None)
        session.pop('_cached_notifs', None)
        session.pop('_cached_unread', None)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error clearing notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

