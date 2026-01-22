"""
Slice of Life routes - Collaborative storytelling (Cassius's Feature)
Flow: Create → Choose Recipients → Waiting Room → Review → Publish
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

slice_of_life_bp = Blueprint('slice_of_life', __name__)

# ============================================
# MAIN FLOW ROUTES
# ============================================

@slice_of_life_bp.route('/prompt')
def prompt():
    """Display the current text prompt for storytelling."""
    user_state = session.get('sol_state', 'new')
    return render_template('slice_of_life/prompt.html', user_state=user_state)


@slice_of_life_bp.route('/create', methods=['GET', 'POST'])
def create_display():
    """Step 1: Create submission with image + story, then go to choose recipients."""
    if request.method == 'POST':
        image = request.files.get('image')
        story = request.form.get('story')
        
        if image and story:
            # TODO: Save image and story to database/session
            session['sol_submission'] = {'story': story}
            return redirect(url_for('slice_of_life.choose_recipients'))
        else:
            flash('Please upload an image and write your story.', 'warning')
    
    return render_template('slice_of_life/create_display.html')


@slice_of_life_bp.route('/choose-recipients', methods=['GET'])
def choose_recipients():
    """Step 2: Choose up to 3 recipients to send invite."""
    return render_template('slice_of_life/choose_recipients.html')


@slice_of_life_bp.route('/send-invites', methods=['POST'])
def send_invites():
    """Step 3: Send invites to selected recipients, go to waiting room."""
    recipients = request.form.getlist('recipients')
    
    if not recipients:
        flash('Please select at least one person.', 'warning')
        return redirect(url_for('slice_of_life.choose_recipients'))
    
    # Store selected recipients in session
    session['sol_recipients'] = recipients
    session['sol_state'] = 'waiting'
    
    flash(f'Invites sent to {len(recipients)} people!', 'success')
    return redirect(url_for('slice_of_life.waiting_room'))


@slice_of_life_bp.route('/waiting-room')
def waiting_room():
    """Step 4: Waiting room showing invite status (instant Received! for demo)."""
    recipients = session.get('sol_recipients', [])
    return render_template('slice_of_life/waiting_room.html', recipients=recipients)


@slice_of_life_bp.route('/review/<int:display_id>', methods=['GET', 'POST'])
def review(display_id):
    """Step 5: Review mode - see both submissions, comment, and publish."""
    if request.method == 'POST':
        comment = request.form.get('comment')
        if comment:
            flash('Comment added!', 'success')
    
    return render_template('slice_of_life/review.html', display_id=display_id)


@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
def publish(display_id):
    """Step 6: Publish with Public AND/OR Private options."""
    # Get both publish options (checkboxes, not radio)
    publish_public = request.form.get('publish_public') == 'on'
    publish_private = request.form.get('publish_private') == 'on'
    
    if not publish_public and not publish_private:
        flash('Please select at least one publish option.', 'warning')
        return redirect(url_for('slice_of_life.review', display_id=display_id))
    
    # TODO: Save to database with privacy settings
    
    # Build success message
    destinations = []
    if publish_public:
        destinations.append('Public Catalog')
    if publish_private:
        destinations.append('Private Collection')
    
    # Reset state
    session['sol_state'] = 'new'
    session.pop('sol_submission', None)
    session.pop('sol_recipients', None)
    
    flash(f'Published to {" and ".join(destinations)}! +10 points earned.', 'success')
    return redirect(url_for('slice_of_life.waiting_room'))


# ============================================
# CATALOG ROUTES
# ============================================

@slice_of_life_bp.route('/catalog')
def catalog():
    """View public catalog of Slice of Life displays."""
    return render_template('slice_of_life/catalog.html', catalog_type='public')


@slice_of_life_bp.route('/catalog/private')
def catalog_private():
    """View user's private Slice of Life displays."""
    return render_template('slice_of_life/catalog.html', catalog_type='private')


@slice_of_life_bp.route('/display/<int:display_id>')
def view_display(display_id):
    """View a specific Slice of Life display."""
    return render_template('slice_of_life/catalog.html', display_id=display_id)


@slice_of_life_bp.route('/like/<int:display_id>', methods=['POST'])
def like_display(display_id):
    """Like a Slice of Life display."""
    flash('You liked this display!', 'success')
    return redirect(url_for('slice_of_life.catalog'))


# ============================================
# RECEIVER ROUTES
# ============================================

@slice_of_life_bp.route('/respond/<int:invite_id>', methods=['GET', 'POST'])
def receiver_respond(invite_id):
    """Receiver responds to an invite with their photo + comment."""
    if request.method == 'POST':
        # TODO: Save receiver's response
        return redirect(url_for('slice_of_life.receiver_waiting'))
    
    return render_template('slice_of_life/receiver_respond.html', invite_id=invite_id)


@slice_of_life_bp.route('/waiting-response')
def receiver_waiting():
    """Receiver waits for sender to review and publish."""
    return render_template('slice_of_life/receiver_waiting.html')


# ============================================
# DEMO ROUTES - For testing
# ============================================

@slice_of_life_bp.route('/demo/set-state/<state>')
def demo_set_state(state):
    """Demo route to set user state manually."""
    if state in ['new', 'waiting', 'ready']:
        session['sol_state'] = state
        flash(f'Demo: State set to "{state}"', 'info')
    return redirect(url_for('slice_of_life.prompt'))
