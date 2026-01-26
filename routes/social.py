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
            
        # Insert friendship
        insert('friendships', {
            'user_id_1': current_user_id,
            'user_id_2': target_id,
            'status': 'pending'
        })

        # Insert notification
        insert('notifications', {
            'user_id': target_id,
            'type': 'friend_request',
            'message': f"{session.get('username')} sent you a friend request!",
            'link': url_for('social.social_hub'),
            'is_read': False
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
    """Get accepted friends, sorted by most recent message."""
    try:
        current_user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get friendships where status is accepted and involves current user
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
            user_data = fetch_one('users', user_id=friend_id)
            if user_data:
                # Get last message
                last_msg = None
                last_msg_time = None
                try:
                    msg_res = supabase.table('messages').select('*').or_(
                        f"and(sender_id.eq.{current_user_id},receiver_id.eq.{friend_id}),and(sender_id.eq.{friend_id},receiver_id.eq.{current_user_id})"
                    ).order('sent_at', desc=True).limit(1).execute()
                    if msg_res.data:
                        last_msg = msg_res.data[0]
                        last_msg_time = last_msg.get('sent_at')
                except:
                    pass
                
                preview = ''
                if last_msg:
                    prefix = 'You: ' if last_msg['sender_id'] == current_user_id else ''
                    preview = f"{prefix}{last_msg['content'][:30]}"
                
                # Determine online status from last_seen
                status = 'Active now' if is_online(user_data) else 'Offline'
                
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
                    'lastMessage': preview,
                    'status': status,
                    'lastMessageTime': last_msg_time,
                    'unreadCount': unread_count
                })
        
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


@social_bp.route('/api/upload_image', methods=['POST'])
def upload_chat_image():
    """Upload an image for chat."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            import os
            from werkzeug.utils import secure_filename
            
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
            'time': m['sent_at'],
            'read': m.get('read', False),
            'image_url': m.get('image_url')
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
        # Fetch Questions
        q_res = supabase.table('questions').select('*').order('created_at', desc=True).execute()
        questions = q_res.data if q_res.data else []
        
        # Fetch Replies
        r_res = supabase.table('replies').select('*').order('created_at').execute() 
        all_raw_replies = r_res.data if r_res.data else []
        
        # Organize Nesting
        reply_map = {r['reply_id']: r for r in all_raw_replies}
        for r in all_raw_replies: r['sub_replies'] = [] # Init
        
        top_level_replies = []
        for r in all_raw_replies:
            pid = r.get('parent_reply_id')
            if pid and pid in reply_map:
                reply_map[pid]['sub_replies'].append(r)
            elif not pid:
                top_level_replies.append(r)
        
        # Attach to questions (Top Level Only)
        for q in questions:
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
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    current_user_id = get_current_user_id()
    current_username = "Jeremy Khoo" # Default fallback
    if current_user_id:
        try:
            u = fetch_one('users', user_id=current_user_id)
            if u: current_username = u.get('username')
        except: pass
        
    return render_template('social/ask_grandfriend.html', questions=questions, current_user_id=current_user_id, current_username=current_username)

@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        user_id = get_current_user_id()
        if not user_id:
            from flask import flash
            flash("Please log in to ask a question.", "warning")
            return redirect(url_for('auth.login'))
            
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

        if title:
            success = False
            try:
                # Try inserting with user_id (New Schema)
                insert('questions', {
                    'title': title,
                    'content': content,
                    'category': category,
                    'author_name': 'Anonymous' if is_anonymous else author_name,
                    'author_type': author_type,
                    'is_anonymous': is_anonymous,
                    'user_id': user_id
                })
                success = True
            except Exception as e:
                print(f"Error posting with user_id: {e}")
                # Fallback to Old Schema (no user_id column)
                try:
                    insert('questions', {
                        'title': title,
                        'content': content,
                        'category': category,
                        'author_name': 'Anonymous' if is_anonymous else author_name,
                        'author_type': author_type,
                        'is_anonymous': is_anonymous
                    })
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

    try:
        data = {
            'question_id': question_id,
            'user_id': user_id,
            'content': content,
            'author_name': author_name,
            'author_type': author_type
        }
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


@social_bp.route('/ask-grandfriend/delete/<question_id>', methods=['POST'])
def delete_question_route(question_id):
    """Delete a question."""
    try:
        supabase = get_supabase()
        supabase.table('questions').delete().eq('id', question_id).execute()
    except Exception as e:
        print(f"Error deleting question: {e}")
    return redirect(url_for('social.ask_grandfriend'))


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
