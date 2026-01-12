"""
Slice of Life routes - Collaborative storytelling (YOUR FEATURE)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

slice_of_life_bp = Blueprint('slice_of_life', __name__)

@slice_of_life_bp.route('/prompt')
def prompt():
    """Display the current text prompt for storytelling."""
    # TODO: Fetch current prompt from database
    # TODO: Fetch pending and ready-for-review displays
    return render_template('slice_of_life/prompt.html')

@slice_of_life_bp.route('/create', methods=['GET', 'POST'])
def create_display():
    """Create a new Slice of Life submission with image upload."""
    if request.method == 'POST':
        # TODO: Handle image upload
        # TODO: Save story and image to database
        # TODO: Check if partner has also submitted
        image = request.files.get('image')
        story = request.form.get('story')
        
        if image and story:
            # Save submission
            flash('Your response has been submitted! Waiting for your partner...', 'success')
            return redirect(url_for('slice_of_life.prompt'))
        else:
            flash('Please upload an image and write your story.', 'warning')
    
    return render_template('slice_of_life/create_display.html')

@slice_of_life_bp.route('/review/<int:display_id>', methods=['GET', 'POST'])
def review(display_id):
    """Review mode - see both submissions and comment."""
    if request.method == 'POST':
        # Handle adding comments
        comment = request.form.get('comment')
        if comment:
            # TODO: Save comment to database
            flash('Comment added!', 'success')
    
    # TODO: Fetch both submissions for this display
    return render_template('slice_of_life/review.html', display_id=display_id)

@slice_of_life_bp.route('/publish/<int:display_id>', methods=['POST'])
def publish(display_id):
    """Publish the display to catalog with privacy settings."""
    privacy = request.form.get('privacy', 'public')
    
    # TODO: Update display status to published
    # TODO: Set privacy setting
    
    flash(f'Display published as {privacy}! You earned +10 points.', 'success')
    return redirect(url_for('slice_of_life.catalog'))

@slice_of_life_bp.route('/catalog')
def catalog():
    """View the catalog of all public Slice of Life displays."""
    # TODO: Fetch displays from database with filters
    return render_template('slice_of_life/catalog.html')

@slice_of_life_bp.route('/display/<int:display_id>')
def view_display(display_id):
    """View a specific Slice of Life display."""
    # TODO: Fetch display details
    return render_template('slice_of_life/catalog.html', display_id=display_id)

@slice_of_life_bp.route('/like/<int:display_id>', methods=['POST'])
def like_display(display_id):
    """Like a Slice of Life display."""
    # TODO: Increment like count in database
    return redirect(url_for('slice_of_life.catalog'))
