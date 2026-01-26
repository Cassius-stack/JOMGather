"""
Slice of Life routes - Collaborative storytelling
Flow: Create → Choose Recipients → Waiting Room → Review → Publish
Supabase Integration: Uses sol_ tables in Cloud DB
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.supabase_db import fetch_all, fetch_one, insert, update, upload_file, get_supabase
from utils.deepseek_client import generate_memory_title
from utils.auth_middleware import login_required
from datetime import datetime, timedelta

slice_of_life_bp = Blueprint('slice_of_life', __name__)

def get_current_user_id():
    return session.get('user_id')

# ============================================
# MAIN FLOW ROUTES
# ============================================

@slice_of_life_bp.route('/')
@login_required
def index():
    """Smart router: Go to waiting room if pending, else prompt."""
    current_uid = get_current_user_id()
    # Check for ANY pending displays (as creator or partner)
    # We'll see if there's anything not 'completed'
    pending_creator = fetch_all('sol_displays', creator_id=current_uid, status='pending')
    pending_partner = fetch_all('sol_displays', partner_id=current_uid, status='pending')
    
    # If forced to start new (from button in waiting room), skip to prompt
    if request.args.get('force_new'):
        return redirect(url_for('slice_of_life.prompt'))

    if pending_creator or pending_partner:
        return redirect(url_for('slice_of_life.waiting_room'))
    
    return redirect(url_for('slice_of_life.prompt'))

@slice_of_life_bp.route('/prompt')
@login_required
def prompt():
    """Display the current daily prompt."""
    today = datetime.now().date().isoformat()
    current_uid = get_current_user_id()
    
    # 1. Check if we already have a prompt for today
    existing_prompt = fetch_all('sol_prompts', active_date=today)
    
    if existing_prompt:
        prompt_data = existing_prompt[0]
    else:
        # 2. Generate new prompt using DeepSeek
        from utils.deepseek_client import generate_daily_question
        recent_prompts = fetch_all('sol_prompts') 
        previous_texts = [p['prompt_text'] for p in recent_prompts[-5:]] if recent_prompts else []
        new_question = generate_daily_question(previous_texts)
        
        # 3. Save to DB
        insert('sol_prompts', {'prompt_text': new_question, 'active_date': today})
        # Re-fetch to get ID
        prompt_data = fetch_all('sol_prompts', active_date=today)[0]
    
    # Removed 1-per-day restriction to allow "Stacking"
    # User can now create multiple slices for the same prompt or different ones.
            
    session['sol_prompt_id'] = prompt_data['prompt_id']
    user_state = session.get('sol_state', 'new')
    
    return render_template('slice_of_life/prompt.html', 
                         prompt=prompt_data, 
                         user_state=user_state)


@slice_of_life_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_display():
    """Step 1: Create submission with image + story."""
    # Fetch prompt for display
    today = datetime.now().date().isoformat()
    prompts = fetch_all('sol_prompts', active_date=today)
    prompt = prompts[0] if prompts else {'prompt_text': 'What is your story for today?'}

    if request.method == 'POST':
        story = request.form.get('story')
        image_file = request.files.get('image') # Get the file object
        
        # Upload Image to Supabase Storage
        image_url = ""
        if image_file and image_file.filename != '':
            import time
            # Use a specific path logic: uploads/{user_id}/{timestamp}_{filename}
            # But simple unique filename is okay for MVP
            filename = f"{int(time.time())}_{image_file.filename}"
            # Upload and get URL
            image_url = upload_file(image_file, bucket='images', path=filename)
        
        # Fallback if no URL/File provided
        if not image_url:
             image_url = "https://i.pravatar.cc/300?img=10" 
        
        if story:
            session['sol_submission'] = {
                'story': story,
                'image_url': image_url
            }
            # Ensure prompt ID is set if user jumped straight here
            if 'sol_prompt_id' not in session and 'prompt_id' in prompt:
                session['sol_prompt_id'] = prompt['prompt_id']
                
            return redirect(url_for('slice_of_life.choose_recipients'))
        else:
            flash('Please provide a story.', 'warning')
    
    return render_template('slice_of_life/create_display.html', prompt=prompt)


@slice_of_life_bp.route('/choose-recipients', methods=['GET'])
@login_required
def choose_recipients():
    """Step 2: Choose recipients from Friends list."""
    current_uid = get_current_user_id()
    search_q = request.args.get('q', '').lower()
    page = int(request.args.get('page', 1))
    limit = 9
    offset = (page - 1) * limit

    # 1. Fetch friend IDs
    friendships = fetch_all('friendships', status='accepted')
    friend_ids = []
    for f in friendships:
        if f['user_id_1'] == current_uid:
            friend_ids.append(f['user_id_2'])
        elif f['user_id_2'] == current_uid:
            friend_ids.append(f['user_id_1'])

    if not friend_ids:
        return render_template('slice_of_life/choose_recipients.html', friends=[], has_more=False, page=page, search_q=search_q)

    # 2. Fetch friend details (manually filtering for now since fetch_all is simple)
    # In a real app: supabase.table('users').select('*').in_('user_id', friend_ids)...
    all_users = fetch_all('users')
    friends = []
    for u in all_users:
        if u['user_id'] in friend_ids:
            # Apply search filter
            if search_q and search_q not in u['username'].lower() and search_q not in u['email'].lower():
                continue
            
            # Add activity status
            is_active = False
            if u.get('last_seen'):
                try:
                    last_seen_dt = datetime.fromisoformat(u['last_seen'].replace('Z', '+00:00'))
                    if datetime.now(last_seen_dt.tzinfo) - last_seen_dt < timedelta(minutes=5):
                        is_active = True
                except:
                    pass
            u['is_active'] = is_active
            friends.append(u)

    # 3. Sort by active status first, then username
    friends.sort(key=lambda x: (not x['is_active'], x['username']))

    # 4. Pagination
    total_found = len(friends)
    paginated_friends = friends[offset:offset + limit]
    has_more = total_found > (offset + limit)

    return render_template('slice_of_life/choose_recipients.html', 
                         friends=paginated_friends, 
                         has_more=has_more, 
                         page=page, 
                         search_q=search_q)


@slice_of_life_bp.route('/send-invites', methods=['POST'])
@login_required
def send_invites():
    """Step 3: Create Display, Submission, and Invites in Supabase."""
    recipients = request.form.getlist('recipients')
    submission_data = session.get('sol_submission')
    prompt_id = session.get('sol_prompt_id')
    sender_id = get_current_user_id()
    
    if not recipients or not submission_data or not prompt_id:
        flash('Missing information. Please start over.', 'danger')
        return redirect(url_for('slice_of_life.prompt'))

    try:
        display_ids = []
        
        # Fetch prompt text for the rich card message
        prompt_data = fetch_one('sol_prompts', prompt_id=prompt_id)
        prompt_text = prompt_data['prompt_text'] if prompt_data else "a daily prompt"

        # Loop through ALL recipients
        for recipient_id_str in recipients:
            recipient_id = int(recipient_id_str)
            
            # 0. Safety Check: No Self-Invite
            if recipient_id == sender_id:
                continue

            # 0. DEBOUNCING: Check for existing unread invite from this sender to this recipient for this prompt
            existing_invites = fetch_all('sol_invites', sender_id=sender_id, recipient_id=recipient_id, prompt_id=prompt_id, status='pending')
            if existing_invites:
                continue

            # 1. Create DISPLAY Record (One per pair)
            display = insert('sol_displays', {
                'prompt_id': prompt_id,
                'creator_id': sender_id,
                'partner_id': recipient_id,
                'status': 'pending',
                'is_public': False,
                'is_private': True
            })
            
            display_id = display['display_id']
            display_ids.append(display_id)

            # 2. Save SENDER's Submission (Duplicate entry per display to link correctly)
            insert('sol_submissions', {
                'display_id': display_id,
                'user_id': sender_id,
                'image_url': submission_data['image_url'],
                'thought': submission_data['story']
            })

            # 3. Create INVITE
            invite = insert('sol_invites', {
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'prompt_id': prompt_id,
                'display_id': display_id,
                'status': 'pending'
            })
            
            # 4. Create NOTIFICATION for Recipient
            insert('notifications', {
                'user_id': recipient_id,
                'type': 'sol_invite',
                'message': f"You have been invited to a Slice of Life conversation!",
                'link': url_for('slice_of_life.receiver_respond', invite_id=invite['invite_id'])
            })
            
            # 5. Send Chat Message (Rich Card)
            # Use RELATIVE URL for href to ensure it works on tunnel/cloud
            invite_href = url_for('slice_of_life.receiver_respond', invite_id=invite['invite_id'], _external=False)
            
            msg_content = (
                f'<div style="background: white; border: 1px solid #cbd5e1; border-radius: 16px; padding: 16px; width: 100%; max-width: 280px; font-family: sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
                f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">'
                f'<span style="font-size: 1.2rem;">🎨</span>'
                f'<strong style="color: #1e3a5f; font-size: 1rem;">Slice of Life Invite</strong>'
                f'</div>'
                f'<p style="color: #64748b; font-size: 0.9rem; margin: 0 0 12px 0;">Let\'s share a moment about: <em>"{prompt_text}"</em></p>'
                f'<a href="{invite_href}" style="display: block; width: 100%; background: #2563eb; color: white; text-align: center; padding: 10px 0; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem;">View & Respond</a>'
                f'</div>'
            )
            insert('messages', {
                'sender_id': sender_id,
                'receiver_id': recipient_id,
                'content': msg_content,
                'read': False
            })

        # 6. Clear Session & Update State
        session.pop('sol_submission', None)
        # We store the LAST display ID or just flag that we are waiting
        session['sol_active_display_id'] = display_ids[0] 
        session['sol_state'] = 'waiting'
        
        flash(f'Invites sent to {len(display_ids)} friends!', 'success')
        return redirect(url_for('slice_of_life.waiting_room'))

    except Exception as e:
        print(f"Error sending invites: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('slice_of_life.prompt'))


@slice_of_life_bp.route('/waiting-room')
@login_required
def waiting_room():
    """Step 4: Sender or Partner waits for response. Supports multiple pending slices."""
    current_uid = get_current_user_id()
    
    # Fetch ALL invites where I am involved (Sender or Recipient)
    # We want invites that are 'pending' or 'accepted' (waiting for publish)
    # Note: 'published' slices move to completion.
    
    # 1. Fetch where I am SENDER
    sent = fetch_all('sol_invites', sender_id=current_uid)
    # 2. Fetch where I am RECIPIENT
    received = fetch_all('sol_invites', recipient_id=current_uid)
    
    all_invites = sent + received
    
    # Filter to only show those that aren't 'published' yet
    # We check the display status
    view_data = []
    
    for invite in all_invites:
        display = fetch_one('sol_displays', display_id=invite['display_id'])
        if display and display['status'] == 'pending':
            is_me_sender = (invite['sender_id'] == current_uid)
            partner_id = invite['recipient_id'] if is_me_sender else invite['sender_id']
            
            # Fetch partner info
            partner = fetch_one('users', user_id=partner_id)
            partner_name = partner['username'] if partner else f"User {partner_id}"
            
            # Fetch query prompt text
            prompt = fetch_one('sol_prompts', prompt_id=invite['prompt_id'])
            
            # Fetch My Submission for this display
            my_subs = fetch_all('sol_submissions', display_id=invite['display_id'], user_id=current_uid)
            my_sub = my_subs[0] if my_subs else None
            
            view_data.append({
                'invite': invite,
                'display': display,
                'partner_name': partner_name,
                'is_me_sender': is_me_sender,
                'prompt_text': prompt['prompt_text'] if prompt else "Daily Prompt",
                'my_submission': my_sub
            })

    # Sort by created_at desc (newest first)
    view_data.sort(key=lambda x: x['invite']['invite_id'], reverse=True)
    
    # If no pending items, but we landed here, maybe they just finished.
    # We'll let the template handle the empty state with a "Start New" button.
    
    return render_template('slice_of_life/waiting_room.html', items=view_data)


@slice_of_life_bp.route('/review/<int:display_id>', methods=['GET', 'POST'])
@login_required
def review(display_id):
    """Step 5: Review mode (and View mode for Catalog)."""
    # Fetch all submissions for this display
    submissions = fetch_all('sol_submissions', display_id=display_id)
    display = fetch_one('sol_displays', display_id=display_id)
    prompt = fetch_one('sol_prompts', prompt_id=display['prompt_id'])
    
    # Fetch interactions
    comments = fetch_all('sol_comments', display_id=display_id)
    # Enrich comments with username (mock join)
    # In real app: select *, users(username) from sol_comments...
    # Here: fetch user for each comment (inefficient but works for prototype)
    for c in comments:
        u = fetch_one('users', user_id=c['user_id'])
        c['username'] = u['username'] if u else 'Unknown'
        
    likes = fetch_all('sol_likes', display_id=display_id)
    like_count = len(likes)
    has_liked = any(l['user_id'] == get_current_user_id() for l in likes)
    
    # Fetch partner info
    partner_id = display['partner_id'] if display['creator_id'] == get_current_user_id() else display['creator_id']
    partner = fetch_one('users', user_id=partner_id)

    if request.method == 'POST':
        # This POST block handles the 'Partner Comment' (the one being renamed)
        comment = request.form.get('comment')
        for sub in submissions:
            if sub['user_id'] != get_current_user_id():
                update('sol_submissions', {'comment': comment}, submission_id=sub['submission_id'])
                flash('Comment added!', 'success')
                # Refresh submissions
                submissions = fetch_all('sol_submissions', display_id=display_id)
    
    # Sort submissions: Current user ALWAYS first (on the left)
    submissions.sort(key=lambda x: x['user_id'] != get_current_user_id())
    
    return render_template('slice_of_life/review.html', 
                         display=display, 
                         prompt=prompt, 
                         submissions=submissions, 
                         current_user_id=get_current_user_id(),
                         partner=partner,
                         comments=comments,
                         like_count=like_count,
                         has_liked=has_liked)


@slice_of_life_bp.route('/edit-story/<int:submission_id>', methods=['POST'])
@login_required
def edit_my_story(submission_id):
    """Allow user to edit their own thought/story before publishing."""
    submission = fetch_one('sol_submissions', submission_id=submission_id)
    if not submission or submission['user_id'] != get_current_user_id():
        flash('Unauthorized or submission not found', 'danger')
        return redirect(url_for('slice_of_life.index'))
    
    new_story = request.form.get('story')
    if new_story:
        update('sol_submissions', {'thought': new_story}, submission_id=submission_id)
        flash('Story updated!', 'success')
    
    return redirect(url_for('slice_of_life.review', display_id=submission['display_id']))


@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
@login_required
def publish(display_id):
    """Step 6: Publish."""
    # Logic for visibility checkboxes
    publish_public = request.form.get('publish_public') == 'on'
    publish_private = request.form.get('publish_private') == 'on'
    
    # 0. Generate AI Title (Poetic summary of thoughts)
    submissions = fetch_all('sol_submissions', display_id=display_id)
    thoughts = [s['thought'] for s in submissions if s['thought']]
    ai_title = generate_memory_title(thoughts)

    # 1. Update Display Status
    update('sol_displays', {
        'status': 'completed',
        'is_public': publish_public,
        'is_private': publish_private,
        'title': ai_title,
        'completed_at': datetime.now().isoformat()
    }, display_id=display_id)
    
    # 2. Notify Partner
    # Find partner ID
    display = fetch_one('sol_displays', display_id=display_id)
    current_uid = get_current_user_id()
    if display:
        partner_id = display['partner_id'] if display['creator_id'] == current_uid else display['creator_id']
        insert('notifications', {
            'user_id': partner_id,
            'type': 'sol_complete',
            'message': f"Your Slice of Life has been published!",
            'link': url_for('slice_of_life.catalog') # Or direct link to view
        })

    # 3. Award Coins & Update Streaks
    try:
        supabase = get_supabase()
        today_date = datetime.now().date()
        yesterday_date = today_date - timedelta(days=1)
        
        # Award coins to publisher
        # Check if user has coin record
        coin_res = supabase.table('coins').select('total_coins').eq('user_id', current_uid).execute()
        if coin_res.data:
            new_coins = coin_res.data[0]['total_coins'] + 10
            supabase.table('coins').update({'total_coins': new_coins}).eq('user_id', current_uid).execute()
        else:
            supabase.table('coins').insert({'user_id': current_uid, 'total_coins': 10}).execute()
            
        # Update Streak
        user_data = fetch_one('users', user_id=current_uid)
        current_streak = user_data.get('sol_streak', 0)
        last_date_str = user_data.get('last_sol_date')
        
        new_streak = current_streak
        should_update_date = True
        
        if not last_date_str:
            new_streak = 1
        else:
            last_date = datetime.fromisoformat(last_date_str).date()
            if last_date == today_date:
                should_update_date = False
            elif last_date == yesterday_date:
                new_streak += 1
            else:
                new_streak = 1
                
        if should_update_date:
            update('users', {
                'sol_streak': new_streak,
                'last_sol_date': today_date.isoformat()
            }, user_id=current_uid)
            
    except Exception as e:
        print(f"Error awarding points/streak: {e}")
    
    session['sol_state'] = 'new'
    session.pop('sol_active_display_id', None)
    
    flash('Published successfully! +10 coins earned and streak updated.', 'success')
    return redirect(url_for('slice_of_life.catalog'))


# ============================================
# CATALOG ROUTES
@slice_of_life_bp.route('/publish_display/<int:display_id>', methods=['POST'])
@login_required
def publish_display(display_id):
    """Publish a completed display to the public gallery."""
    current_uid = get_current_user_id()
    
    # Verify ownership
    display = fetch_one('sol_displays', display_id=display_id)
    if not display:
        return jsonify({'success': False, 'error': 'Display not found'}), 404
        
    if display['creator_id'] != current_uid and display['partner_id'] != current_uid:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    # GATE: Check if BOTH parties have commented?
    # Actually, logic says "Wait for both to respond". That is already done if we are in Review Mode.
    # User said "do NOT allow publishing until both parties have commented."
    # Comments are in 'sol_comments'. We need to check if unique user_ids in comments >= 2.
    comments = fetch_all('sol_comments', display_id=display_id)
    commenters = set(c['user_id'] for c in comments)
    
    # Must have at least 2 unique commenters (Creator + Partner usually)
    # Or just ensure current user + partner have commented?
    # Simple check: len(commenters) >= 2
    if len(commenters) < 2:
        return jsonify({
            'success': False, 
            'error': 'Both partners must comment on the memory before publishing! Share your thoughts first.'
        }), 400

    # Publish
    update('sol_displays', {'is_public': True, 'is_private': False}, display_id=display_id)
    
    flash('Successfully published to the Memory Library!', 'success')
    return jsonify({'success': True, 'redirect': url_for('slice_of_life.catalog')})


@slice_of_life_bp.route('/like/<int:display_id>', methods=['POST'])
@login_required
def like_display(display_id):
    """Toggle like on a display."""
    user_id = get_current_user_id()
    
    # Check if already liked
    existing_like = fetch_all('sol_likes', user_id=user_id, display_id=display_id)
    
    if existing_like:
        # Unlike
        # (Assuming we have a delete helper, otherwise raw SQL or skip)
        # For simplicity in this mock wrapper, we'll try to find a way to delete or just ignore
        # If no delete helper, we might just return (prototype limitation)
        # But 'supabase_db' usually has `supabase.table().delete()`
        from utils.supabase_db import get_supabase
        get_supabase().table('sol_likes').delete().eq('user_id', user_id).eq('display_id', display_id).execute()
        flash('Unliked.', 'info')
    else:
        # Like
        insert('sol_likes', {'user_id': user_id, 'display_id': display_id})
        
        # Notify creator/partner (whoever didn't like it)
        display = fetch_one('sol_displays', display_id=display_id)
        if display:
            creator_id = display['creator_id']
            partner_id = display['partner_id']
            target_id = creator_id if user_id != creator_id else partner_id
            
            insert('notifications', {
                'user_id': target_id,
                'type': 'sol_like',
                'message': f"Someone liked your Slice of Life!",
                'link': url_for('slice_of_life.review', display_id=display_id)
            })
        flash('Liked!', 'success')
        
    return redirect(request.referrer or url_for('slice_of_life.catalog'))


@slice_of_life_bp.route('/comment/<int:display_id>', methods=['POST'])
@login_required
def post_comment(display_id):
    """Post a public comment."""
    content = request.form.get('content')
    if content:
        insert('sol_comments', {
            'display_id': display_id,
            'user_id': get_current_user_id(),
            'content': content
        })
        
        # Notify participants
        display = fetch_one('sol_displays', display_id=display_id)
        if display:
            # Notify both creator and partner (unless they are the commenter)
            creator_id = display['creator_id']
            partner_id = display['partner_id']
            current = get_current_user_id()
            
            for target in [creator_id, partner_id]:
                if target != current:
                    insert('notifications', {
                        'user_id': target,
                        'type': 'sol_comment',
                        'message': f"New comment on your Slice of Life: {content[:30]}...",
                        'link': url_for('slice_of_life.review', display_id=display_id)
                    })
        
        flash('Comment posted.', 'success')
        
    return redirect(url_for('slice_of_life.review', display_id=display_id))


# ============================================

@slice_of_life_bp.route('/catalog')
@login_required
def catalog():
    """View memory catalog with filters."""
    filter_type = request.args.get('filter', 'public')
    current_uid = get_current_user_id()
    
    displays = []
    
    if filter_type == 'public':
        # Public displays (all completed & is_public=True)
        # Ideally ordered by likes (requires adding likes to fetch query or sorting in python)
        displays = fetch_all('sol_displays', status='completed', is_public=True)
        # Mock sorting by random for variety if likes query is complex
        
    elif filter_type == 'private':
        # Private: My displays (creator or partner)
        # Supabase fetch_all is limited to exact matches usually.
        # We need "OR" logic: creator_id=me OR partner_id=me
        # Since our simple helper might not support OR, we can do two fetches
        as_creator = fetch_all('sol_displays', creator_id=current_uid, status='completed')
        as_partner = fetch_all('sol_displays', partner_id=current_uid, status='completed')
        
        # Merge and deduplicate (though IDs should be unique)
        displays_map = {d['display_id']: d for d in as_creator + as_partner}
        displays = list(displays_map.values())
        
    elif filter_type == 'friends':
        # Friend's displays: displays where creator OR partner is my friend AND is_public=True
        # TODO: Implement Friend Logic
        displays = []
    
    # Enrich displays with submissions (images), prompt text, and sorting
    enriched_displays = []
    for d in displays:
        # Prompt details
        p = fetch_one('sol_prompts', prompt_id=d['prompt_id'])
        d['prompt_text'] = p['prompt_text'] if p else "Shared Story"
        
        # Submissions (for combined images)
        subs = fetch_all('sol_submissions', display_id=d['display_id'])
        d['submissions'] = subs
        
        # Like count and has_liked
        l_res = fetch_all('sol_likes', display_id=d['display_id'])
        d['likes'] = len(l_res)
        d['has_liked'] = any(l['user_id'] == current_uid for l in l_res)
        
        # Top 3 Comments
        all_comments = fetch_all('sol_comments', display_id=d['display_id'])
        d['comments_preview'] = all_comments[:3]
        
        enriched_displays.append(d)

    # Sorting: Higher liked on top (only for Public)
    if filter_type == 'public':
        enriched_displays.sort(key=lambda x: x['likes'], reverse=True)
        
    return render_template('slice_of_life/catalog.html', current_filter=filter_type, displays=enriched_displays)


# ============================================
# RECEIVER ROUTES
# ============================================

@slice_of_life_bp.route('/respond/<int:invite_id>', methods=['GET', 'POST'])
@login_required
def receiver_respond(invite_id):
    """Receiver responds to invite."""
    current_uid = get_current_user_id()

    # 1. Fetch Invite
    invite = fetch_one('sol_invites', invite_id=invite_id)
    if not invite:
        return "Invite not found", 404
    
    # 1a. Prompt Expiration Check
    today = datetime.now().date().isoformat()
    current_prompts = fetch_all('sol_prompts', active_date=today)
    if current_prompts and invite['prompt_id'] != current_prompts[0]['prompt_id']:
        return render_template('errors/general_error.html', 
                             title="Invite Expired", 
                             message="This invite was for a previous Daily Prompt. To keep stories together, we only allow responses to the current day's prompt!")

    # 1b. Duplicate Submission Check
    existing_sub = fetch_one('sol_submissions', display_id=invite['display_id'], user_id=current_uid)
    if existing_sub:
        return redirect(url_for('slice_of_life.review', display_id=invite['display_id']))

    # Ensure current user is the recipient
    if invite['recipient_id'] != current_uid:
        flash("You are not authorized to respond to this invite.", "danger")
        return redirect(url_for('main.dashboard')) # Or some other appropriate redirect
        
    # 2. Fetch Display and Sender Submission
    display_id = invite['display_id']
    submissions = fetch_all('sol_submissions', display_id=display_id)
    sender_submission = next((s for s in submissions if s['user_id'] == invite['sender_id']), None)
    
    # 3. Fetch Prompt and Sender Details
    prompt = fetch_one('sol_prompts', prompt_id=invite['prompt_id'])
    sender = fetch_one('users', user_id=invite['sender_id'])

    if request.method == 'POST':
        story = request.form.get('story')
        image = request.files.get('image') # Get the file object
        
        image_url = None
        if image and image.filename != '':
            import time
            filename = f"resp_{int(time.time())}_{image.filename}"
            image_url = upload_file(image, bucket='images', path=filename)
        
        if not image_url:
            image_url = "https://i.pravatar.cc/300?img=25"
        
        # Save Submission
        insert('sol_submissions', {
            'display_id': invite['display_id'],
            'user_id': current_uid,
            'image_url': image_url,
            'thought': story
        })
        
        # Update Invite Status
        update('sol_invites', {
            'status': 'accepted', 
            'responded_at': datetime.now().isoformat()
        }, invite_id=invite_id)
        
        # Notify Sender
        insert('notifications', {
            'user_id': invite['sender_id'],
            'type': 'sol_accept', # or sol_response
            'message': f"Your partner responded to your Slice of Life!",
            'link': url_for('slice_of_life.review', display_id=display_id)
        })
        
        return redirect(url_for('slice_of_life.review', display_id=display_id))
    
    return render_template('slice_of_life/receiver_respond.html', 
                         invite=invite, 
                         prompt=prompt,
                         sender=sender) 
                         # Removed sender_submission to keep it 'Blind Box'


@slice_of_life_bp.route('/waiting-response')
def receiver_waiting():
    """Receiver success page."""
    return render_template('slice_of_life/receiver_waiting.html')
