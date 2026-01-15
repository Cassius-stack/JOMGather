"""
Slice of Life routes - Collaborative storytelling (YOUR FEATURE)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

slice_of_life_bp = Blueprint('slice_of_life', __name__)

@slice_of_life_bp.route('/prompt')
def prompt():
    """Display the current text prompt for storytelling."""
    # Get user's current state for this feature
    # States: 'new' (hasn't done activity), 'waiting' (submitted, partner hasn't), 'ready' (both submitted)
    
    # For demo purposes, check session or default to 'new'
    user_state = session.get('sol_state', 'new')
    
    return render_template('slice_of_life/prompt.html', user_state=user_state)

@slice_of_life_bp.route('/create', methods=['GET', 'POST'])
def create_display():
    """Create a new Slice of Life submission with image upload."""
    if request.method == 'POST':
        image = request.files.get('image')
        story = request.form.get('story')
        
        if image and story:
            # TODO: Save image and story to database
            
            # Update user state to 'waiting' (submitted, waiting for partner)
            session['sol_state'] = 'waiting'
            
            flash('Your response has been submitted! Waiting for your partner...', 'success')
            return redirect(url_for('slice_of_life.prompt'))
        else:
            flash('Please upload an image and write your story.', 'warning')
    
    return render_template('slice_of_life/create_display.html')

@slice_of_life_bp.route('/review/<int:display_id>', methods=['GET', 'POST'])
def review(display_id):
    """Review mode - see both submissions and comment."""
    if request.method == 'POST':
        comment = request.form.get('comment')
        if comment:
            flash('Comment added!', 'success')
    
    return render_template('slice_of_life/review.html', display_id=display_id)

@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
def publish(display_id):
    """Publish the display to catalog with privacy settings."""
    privacy = request.form.get('privacy', 'public')
    
    # Reset user state after publishing
    session['sol_state'] = 'new'
    
    flash(f'Display published as {privacy}! You earned +10 points.', 'success')
    return redirect(url_for('slice_of_life.catalog'))

@slice_of_life_bp.route('/catalog')
def catalog():
    """View the catalog of all public Slice of Life displays."""
    return render_template('slice_of_life/catalog.html')

@slice_of_life_bp.route('/display/<int:display_id>')
def view_display(display_id):
    """View a specific Slice of Life display."""
    return render_template('slice_of_life/catalog.html', display_id=display_id)

@slice_of_life_bp.route('/like/<int:display_id>', methods=['POST'])
def like_display(display_id):
    """Like a Slice of Life display."""
    return redirect(url_for('slice_of_life.catalog'))

# ============================================
# DEMO ROUTES - For testing different states
# ============================================

@slice_of_life_bp.route('/demo/set-state/<state>')
def demo_set_state(state):
    """Demo route to simulate different user states."""
    if state in ['new', 'waiting', 'ready']:
        session['sol_state'] = state
        flash(f'Demo: State set to "{state}"', 'info')
    return redirect(url_for('slice_of_life.prompt'))
