"""
Activities routes - Activity Suite (Brandon's feature)
TikTok Challenges, Puzzle Challenges, Virtual Games, Photo Streak
"""

from flask import Blueprint, render_template, request, redirect, url_for

activities_bp = Blueprint('activities', __name__)

@activities_bp.route('/')
def activity_list():
    """List all available activities."""
    return render_template('activities/activity_list.html')

@activities_bp.route('/tiktok-challenge')
def tiktok_challenge():
    """TikTok video challenges."""
    return render_template('activities/tiktok_challenge.html')

@activities_bp.route('/tiktok-challenge/create', methods=['GET', 'POST'])
def create_tiktok_challenge():
    """Create a new TikTok challenge."""
    if request.method == 'POST':
        # TODO: Save challenge to database
        pass
    return render_template('activities/tiktok_challenge.html')

@activities_bp.route('/puzzle-challenge')
def puzzle_challenge():
    """Cooperative puzzle/brain games."""
    return render_template('activities/puzzle_challenge.html')

@activities_bp.route('/photo-streak')
def photo_streak():
    """Daily photo exchange streak."""
    return render_template('activities/photo_streak.html')

@activities_bp.route('/photo-streak/upload', methods=['POST'])
def upload_photo():
    """Upload a photo for the streak."""
    # TODO: Handle photo upload
    return redirect(url_for('activities.photo_streak'))


@activities_bp.route('/boomerang')
def boomerang():
    """BOOMERang - Description/Setup page."""
    return render_template('activities/Boomerang/Description.html')


@activities_bp.route('/boomerang/meetup')
def boomerang_meetup():
    """BOOMERang - Video call meetup page."""
    return render_template('activities/Boomerang/Meetup.html')


@activities_bp.route('/boomerang/loading')
def boomerang_loading():
    """BOOMERang - Loading/matching page."""
    return render_template('activities/Boomerang/LoadingPage.html')


# === Helper Functions ===
def search_activities_logic(query):
    """Search for activities matching the query."""
    activities = [
        {'name': 'Slice of Life', 'description': 'Share daily photo stories', 'url': url_for('slice_of_life.prompt'), 'icon': 'bi-camera', 'color': 'primary'},
        {'name': 'Support Swap', 'description': 'Exchange skills and help', 'url': url_for('support_swap.ss_profile'), 'icon': 'bi-lightbulb', 'color': 'warning'},
        {'name': 'Jukebox', 'description': 'Share songs and playlists', 'url': url_for('social.social_hub'), 'icon': 'bi-music-note-beamed', 'color': 'info'},
        {'name': 'Cyber Challenge', 'description': 'Digital literacy quiz', 'url': url_for('activities.puzzle_challenge'), 'icon': 'bi-shield-check', 'color': 'danger'},
        {'name': 'BOOMERang', 'description': 'Quick video chat', 'url': url_for('activities.boomerang'), 'icon': 'bi-camera-video', 'color': 'secondary'},
        {'name': 'Puzzle Challenge', 'description': 'Cooperative brain games', 'url': url_for('activities.puzzle_challenge'), 'icon': 'bi-puzzle', 'color': 'success'},
        {'name': 'TikTok Challenge', 'description': 'Viral video challenges', 'url': url_for('activities.tiktok_challenge'), 'icon': 'bi-tiktok', 'color': 'dark'}
    ]
    
    if not query:
        return []
        
    query = query.lower()
    return [a for a in activities if query in a['name'].lower() or query in a['description'].lower()]

