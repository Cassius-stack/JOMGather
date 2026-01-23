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
    # Fetch today's prompt (or the latest one)
    # For now, just get the first one if searching by date is complex
    prompt_data = fetch_one('sol_prompts', columns='*') # Simplified for MVP
    
    if not prompt_data:
        # Fallback if no prompt exists
        prompt_data = {'prompt_id': 0, 'prompt_text': 'No active prompt found.'}
    
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
        # In a real app with Supabase Storage, we would upload the image here.
        # For this MVP, we will simulate the image URL.
        story = request.form.get('story')
        
        # Placeholder image logic 
        # (In Phase 4 part 2, we will add Supabase Storage upload)
        image_url = "https://i.pravatar.cc/300?img=10" 
        
        if story:
            session['sol_submission'] = {
                'story': story,
                'image_url': image_url
            }
            return redirect(url_for('slice_of_life.choose_recipients'))
        else:
            flash('Please upload an image and write your story.', 'warning')
    
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
    
    if not recipients or not submission_data or not prompt_id:
        flash('Missing information. Please start over.', 'danger')
        return redirect(url_for('slice_of_life.prompt'))

    try:
        # 1. Create DISPLAY Record
        # We create one display per recipient (1-on-1 model)
        # OR one display for the group. The requirement seems "Pair" based usually.
        # Let's assume 1-on-1 for simplicity as per "Choose Partner" flow usually.
        # But if multiple selected, we loop? 
        # Let's handle just the FIRST recipient for the MVP to keep it simple 1-on-1.
        recipient_id = int(recipients[0]) 

        display = insert('sol_displays', {
            'prompt_id': prompt_id,
            'creator_id': get_current_user_id(),
            'partner_id': recipient_id,
            'status': 'pending',
            'is_public': False,
            'is_private': True
        })
        
        if not display:
            raise Exception("Failed to create display")
            
        display_id = display['display_id']

        # 2. Save SENDER's Submission
        insert('sol_submissions', {
            'display_id': display_id,
            'user_id': get_current_user_id(),
            'image_url': submission_data['image_url'],
            'thought': submission_data['story']
        })

        # 3. Create INVITE
        insert('sol_invites', {
            'sender_id': get_current_user_id(),
            'recipient_id': recipient_id,
            'prompt_id': prompt_id,
            'display_id': display_id,
            'status': 'pending'
        })

        # 4. Clear Session & Update State
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
    """Step 5: Review mode."""
    # Fetch all submissions for this display
    submissions = fetch_all('sol_submissions', display_id=display_id)
    display = fetch_one('sol_displays', display_id=display_id)
    prompt = fetch_one('sol_prompts', prompt_id=display['prompt_id'])
    
    if request.method == 'POST':
        # Save comment to the PARTNER's submission (usually)
        # or properly a 'comments' table, but our schema added 'comment' to submission
        comment = request.form.get('comment')
        
        # Determine which submission to update (not the current user's)
        for sub in submissions:
            if sub['user_id'] != get_current_user_id():
                update('sol_submissions', {'comment': comment}, submission_id=sub['submission_id'])
                flash('Comment added!', 'success')
                # Refresh submissions to show new comment
                submissions = fetch_all('sol_submissions', display_id=display_id)
    
    return render_template('slice_of_life/review.html', display=display, prompt=prompt, submissions=submissions, current_user_id=get_current_user_id())


@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
@login_required
def publish(display_id):
    """Step 6: Publish."""
    publish_public = request.form.get('publish_public') == 'on'
    publish_private = request.form.get('publish_private') == 'on'
    
    if not publish_public and not publish_private:
        flash('Please select at least one publish option.', 'warning')
        return redirect(url_for('slice_of_life.review', display_id=display_id))
    
    # Update Display Status
    update('sol_displays', {
        'status': 'completed',
        'is_public': publish_public,
        'is_private': publish_private,
        'completed_at': datetime.now().isoformat()
    }, display_id=display_id)
    
    session['sol_state'] = 'new'
    session.pop('sol_active_display_id', None)
    
    flash('Published successfully! +10 points earned.', 'success')
    return redirect(url_for('slice_of_life.catalog'))


# ============================================
# CATALOG ROUTES
# ============================================

@slice_of_life_bp.route('/catalog')
def catalog():
    """View public catalog."""
    # Fetch completed public displays
    displays = fetch_all('sol_displays', status='completed', is_public=True)
    return render_template('slice_of_life/catalog.html', catalog_type='public', displays=displays)


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
        
        # Placeholder image
        image_url = "https://i.pravatar.cc/300?img=25"
        
        # Save Receiver Submission
        insert('sol_submissions', {
            'display_id': display_id,
            'user_id': invite['recipient_id'],
            'image_url': image_url,
            'thought': story
        })
        
        # Update Invite Status
        print("Updating Invite Status to accepted...")
        update('sol_invites', {
            'status': 'accepted', 
            'responded_at': datetime.now().isoformat()
        }, invite_id=invite_id)
        
        return redirect(url_for('slice_of_life.receiver_waiting'))
    
    return render_template('slice_of_life/receiver_respond.html', 
                         invite=invite, 
                         prompt=prompt,
                         sender=sender,
                         sender_submission=sender_submission)


@slice_of_life_bp.route('/waiting-response')
def receiver_waiting():
    """Receiver success page."""
    return render_template('slice_of_life/receiver_waiting.html')
