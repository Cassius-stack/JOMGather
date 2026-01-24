"""
Slice of Life routes - Collaborative storytelling
Flow: Create → Choose Recipients → Waiting Room → Review → Publish
Supabase Integration: Uses sol_ tables in Cloud DB
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.supabase_db import fetch_all, fetch_one, insert, update
from utils.auth_middleware import login_required
from datetime import datetime

slice_of_life_bp = Blueprint('slice_of_life', __name__)

def get_current_user_id():
    return session.get('user_id')

# ============================================
# MAIN FLOW ROUTES
# ============================================

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
    
    # 4. Check if User ALREADY has a display for this prompt
    # Query: Creator IS me OR Partner IS me AND prompt_id IS today's
    user_displays = fetch_all('sol_displays', prompt_id=prompt_data['prompt_id']) # Not efficient but simpler with current helpers
    my_display = next((d for d in user_displays if d['creator_id'] == current_uid or d['partner_id'] == current_uid), None)
    
    if my_display:
        if my_display['status'] == 'completed':
            return redirect(url_for('slice_of_life.catalog')) # Or review
        elif my_display['status'] == 'pending':
            session['sol_active_display_id'] = my_display['display_id']
            # If I am creator and sent invite -> waiting room
            # If I am partner and accepted -> waiting room (or review if done)
            return redirect(url_for('slice_of_life.waiting_room'))
            
    session['sol_prompt_id'] = prompt_data['prompt_id']
    user_state = session.get('sol_state', 'new')
    
    return render_template('slice_of_life/prompt.html', 
                         prompt=prompt_data, 
                         user_state=user_state)


@slice_of_life_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_display():
    """Step 1: Create submission with image + story."""
    if request.method == 'POST':
        story = request.form.get('story')
        image_url = request.form.get('image_url') # Optional URL input if we had one
        
        # Handle File Upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                import os
                from werkzeug.utils import secure_filename
                
                # Ensure uploads dir exists (in static for simple serving)
                upload_folder = os.path.join('static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    
                filename = secure_filename(f"user_{session.get('user_id')}_{int(datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(upload_folder, filename))
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        # Fallback if no URL/File provided
        if not image_url:
             image_url = "https://i.pravatar.cc/300?img=10" 
        
        if story:
            session['sol_submission'] = {
                'story': story,
                'image_url': image_url
            }
            return redirect(url_for('slice_of_life.choose_recipients'))
        else:
            flash('Please provide a story.', 'warning')
    
    return render_template('slice_of_life/create_display.html')


@slice_of_life_bp.route('/choose-recipients', methods=['GET'])
@login_required
def choose_recipients():
    """Step 2: Choose recipients from Friends list."""
    # Fetch friends from Supabase (mock logic for now as 'friends' table might not exist)
    # We will fetch 'users' for now to simulate friends
    friends = fetch_all('users', columns='user_id, username, email, user_type')
    
    # Filter out current user
    current_uid = get_current_user_id()
    friends = [f for f in friends if f['user_id'] != current_uid]
    
    return render_template('slice_of_life/choose_recipients.html', friends=friends)


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
        # 1. Create DISPLAY Record
        recipient_id = int(recipients[0]) 

        display = insert('sol_displays', {
            'prompt_id': prompt_id,
            'creator_id': sender_id,
            'partner_id': recipient_id,
            'status': 'pending',
            'is_public': False,
            'is_private': True
        })
        
        display_id = display['display_id']

        # 2. Save SENDER's Submission
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
        
        # 5. [NEW] Send Chat Message
        msg_content = f"Hey! I just invited you to a daily Slice of Life conversation. Check your notifications or click here to join: {url_for('slice_of_life.receiver_respond', invite_id=invite['invite_id'], _external=True)}"
        insert('messages', {
            'sender_id': sender_id,
            'receiver_id': recipient_id,
            'content': msg_content,
            'read': False
        })

        # 6. Clear Session & Update State
        session.pop('sol_submission', None)
        session['sol_active_display_id'] = display_id
        session['sol_state'] = 'waiting'
        
        flash(f'Invite sent! Waiting for response.', 'success')
        return redirect(url_for('slice_of_life.waiting_room'))

    except Exception as e:
        print(f"Error sending invites: {e}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('slice_of_life.prompt'))


@slice_of_life_bp.route('/waiting-room')
@login_required
def waiting_room():
    """Step 4: Sender waits for response."""
    display_id = session.get('sol_active_display_id')
    if not display_id:
        return redirect(url_for('slice_of_life.prompt'))
        
    # Check Invite Status in Supabase
    # We query sol_invites for this display
    # (In real app, we'd use a more specific query)
    # Using raw SQL might be easier for joins, but let's do two fetches
    
    invites = fetch_all('sol_invites', display_id=display_id)
    invite = invites[0] if invites else None
    
    if invite and invite['status'] == 'accepted':
        # Check if partner has submitted
        submissions = fetch_all('sol_submissions', display_id=display_id)
        if len(submissions) >= 2:
             return redirect(url_for('slice_of_life.review', display_id=display_id))

    return render_template('slice_of_life/waiting_room.html', invite=invite, display_id=display_id)


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
    
    if request.method == 'POST':
        # This POST block handles the 'Partner Comment' (private feedback) 
        # NOT the public comments. Public comments use /comment route.
        comment = request.form.get('comment')
        for sub in submissions:
            if sub['user_id'] != get_current_user_id():
                update('sol_submissions', {'comment': comment}, submission_id=sub['submission_id'])
                flash('Feedback added!', 'success')
                # Refresh submissions
                submissions = fetch_all('sol_submissions', display_id=display_id)
    
    return render_template('slice_of_life/review.html', 
                         display=display, 
                         prompt=prompt, 
                         submissions=submissions, 
                         current_user_id=get_current_user_id(),
                         comments=comments,
                         like_count=like_count,
                         has_liked=has_liked)


@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
@login_required
def publish(display_id):
    """Step 6: Publish."""
    # Logic for visibility checkboxes
    publish_public = request.form.get('publish_public') == 'on'
    publish_private = request.form.get('publish_private') == 'on'
    
    # 1. Update Display Status
    update('sol_displays', {
        'status': 'completed',
        'is_public': publish_public,
        'is_private': publish_private, # If both selected, it appears in both lists
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

    # 3. Award Coins (basic implementation)
    # real app would check 'coins' table and increment
    # update('coins', {'total_coins': current_total + 10}, user_id=current_uid)
    
    session['sol_state'] = 'new'
    session.pop('sol_active_display_id', None)
    
    flash('Published successfully! +10 points earned.', 'success')
    return redirect(url_for('slice_of_life.catalog'))


# ============================================
# CATALOG ROUTES
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
        # This is complex without a robust SQL query builder.
        # MVP: Just show Public for now, or implement basic filtering in Python
        all_public = fetch_all('sol_displays', status='completed', is_public=True)
        
        # Fetch my friends IDs
        # (Assuming we implemented friendships table query)
        # friends = get_my_friend_ids(current_uid)
        # displays = [d for d in all_public if d['creator_id'] in friends or d['partner_id'] in friends]
        
        displays = all_public # Fallback for now to keep it working
        
    return render_template('slice_of_life/catalog.html', current_filter=filter_type, displays=displays)


# ============================================
# RECEIVER ROUTES
# ============================================

@slice_of_life_bp.route('/respond/<int:invite_id>', methods=['GET', 'POST'])
def receiver_respond(invite_id):
    """Receiver responds to invite."""
    # 1. Fetch Invite
    invite = fetch_one('sol_invites', invite_id=invite_id)
    if not invite:
        return "Invite not found", 404
        
    # 2. Fetch Display and Sender Submission
    display_id = invite['display_id']
    submissions = fetch_all('sol_submissions', display_id=display_id)
    sender_submission = submissions[0] if submissions else None
    
    # 3. Fetch Prompt and Sender Details
    prompt = fetch_one('sol_prompts', prompt_id=invite['prompt_id'])
    sender = fetch_one('users', user_id=invite['sender_id'])

    if request.method == 'POST':
        story = request.form.get('story')
        # comment = request.form.get('comment')  # If we want to capture the comment on sender here
        
        # Handle File Upload
        import os
        from werkzeug.utils import secure_filename
        image_url = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                upload_folder = os.path.join('static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                filename = secure_filename(f"user_{invite['recipient_id']}_{int(datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(upload_folder, filename))
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        if not image_url:
            image_url = "https://i.pravatar.cc/300?img=25"
        
        # Save Receiver Submission
        insert('sol_submissions', {
            'display_id': display_id,
            'user_id': invite['recipient_id'],
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
        
        return redirect(url_for('slice_of_life.receiver_waiting'))
    
    return render_template('slice_of_life/receiver_respond.html', 
                         invite=invite, 
                         prompt=prompt,
                         sender=sender) 
                         # Removed sender_submission to keep it 'Blind Box'


@slice_of_life_bp.route('/waiting-response')
def receiver_waiting():
    """Receiver success page."""
    return render_template('slice_of_life/receiver_waiting.html')
