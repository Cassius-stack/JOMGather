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
