"""
Jukebox Routes - Generational Jukebox feature
Allows users to spin a wheel of song recommendations and rate songs  
"""

from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_db import get_supabase, fetch_one
from utils.auth_middleware import login_required
from models.jukebox import get_songs_from_channel, save_song_rating, get_user_spin_history
from datetime import datetime
import random

jukebox_bp = Blueprint('jukebox', __name__)


def get_current_user_id():
    """Get current user ID from session."""
    return session.get('user_id')


def get_current_username():
    """Get current username from session."""
    return session.get('username', 'Unknown')


# ============================================
# MAIN PAGE ROUTE
# ============================================

@jukebox_bp.route('/')
@login_required
def jukebox_page():
    """Main jukebox page with spinning wheel."""
    community_id = request.args.get('community', type=int) or 1  # Default to Musicly (ID 1)
    return render_template('jukebox/juke.html', community_id=community_id)


# ============================================
# API ENDPOINTS
# ============================================

@jukebox_bp.route('/api/songs/<int:community_id>', methods=['GET'])
@login_required
def get_songs(community_id):
    """Get all song recommendations from a community's song channel."""
    try:
        songs = get_songs_from_channel(community_id)
        return jsonify({
            'success': True,
            'songs': songs,
            'count': len(songs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@jukebox_bp.route('/api/spin', methods=['POST'])
@login_required
def spin_wheel():
    """
    Spin the wheel and get a random song.
    Seniors see youth songs, Youth see senior songs (generational exchange).
    """
    try:
        data = request.get_json()
        community_id = data.get('community_id')
        
        if not community_id:
            return jsonify({'success': False, 'error': 'Community ID required'}), 400
        
        # Get current user's info
        user_id = get_current_user_id()
        user = fetch_one('users', 'user_id, user_type', user_id=user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        current_user_type = user.get('user_type', '')
        
        # Determine which songs to show (opposite generation)
        if current_user_type == 'senior':
            # Seniors see youth songs
            filter_type = 'youth'
        elif current_user_type == 'youth':
            # Youth see senior songs
            filter_type = 'senior'
        else:
            # Default: show all songs
            filter_type = None
        
        # Get songs from channel filtered by opposite user type
        songs = get_songs_from_channel(community_id, user_type_filter=filter_type)
        
        if not songs:
            return jsonify({
                'success': False, 
                'error': f'No songs found from {filter_type}s in the recommendations channel. Try adding some songs first!'
            }), 404
        
        # Pick a random song
        selected_song = random.choice(songs)
        
        return jsonify({
            'success': True,
            'song': selected_song
        })
        
    except Exception as e:
        print(f"Error in spin_wheel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@jukebox_bp.route('/api/rate', methods=['POST'])
@login_required
def rate_song():
    """
    Submit a rating for a song.
    Also posts the rating to the community chat.
    """
    try:
        data = request.get_json()
        community_id = data.get('community_id')
        song_id = data.get('song_id')
        song_title = data.get('song_title')
        rating = data.get('rating')
        
        if not all([community_id, song_id, rating]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not (1 <= rating <= 5):
            return jsonify({'success': False, 'error': 'Rating must be 1-5'}), 400
        
        user_id = get_current_user_id()
        username = get_current_username()
        
        # Save the rating
        save_song_rating(user_id, song_id, rating, community_id)
        
        # Post rating to the song recommendations channel
        supabase = get_supabase()
        
        # Find the song recommendations channel
        channel = supabase.table('community_channels').select('*').eq(
            'community_id', community_id
        ).ilike('name', '%song%recommend%').execute()
        
        if channel.data:
            channel_id = channel.data[0]['channel_id']
            
            # Create star rating display
            stars = '⭐' * rating
            rating_message = f"🎵 {username} rated \"{song_title}\" {stars} ({rating}/5) via Generational Jukebox!"
            
            # Post to chat
            supabase.table('community_messages').insert({
                'channel_id': channel_id,
                'user_id': user_id,
                'content': rating_message,
                'created_at': datetime.now().isoformat()
            }).execute()
        
        return jsonify({
            'success': True,
            'message': 'Rating submitted and posted to chat!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@jukebox_bp.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get user's spin history."""
    try:
        user_id = get_current_user_id()
        community_id = request.args.get('community_id', type=int)
        
        history = get_user_spin_history(user_id, community_id)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
