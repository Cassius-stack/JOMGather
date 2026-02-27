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

# Initialize Supabase client
supabase = get_supabase()



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
    try:
        musicly = supabase.table('communities').select('community_id').eq('name', 'Musicly').execute()
        if musicly.data and len(musicly.data) > 0:
            community_id = musicly.data[0]['community_id']
        else:
            community_id = 2
    except Exception as e:
        print(f"Error finding Musicly: {e}")
        community_id = 2

    # Get current user's type so the template knows which wheel to show
    user_id = get_current_user_id()
    user_type = 'youth'  # default
    try:
        user_row = fetch_one('users', 'user_type', user_id=user_id)
        if user_row:
            user_type = user_row.get('user_type', 'youth')
    except Exception as e:
        print(f"Error fetching user type: {e}")

    return render_template('jukebox/juke.html', community_id=community_id, user_type=user_type)


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
    Spin the wheel and get a random song from the OPPOSITE generation.
    Seniors spin to discover youth songs; youth spin to discover senior songs.
    """
    try:
        data = request.get_json()
        community_id = data.get('community_id')
        wheel = data.get('wheel')  # 'youth' or 'senior' - which generation's songs to fetch

        if not community_id:
            return jsonify({'success': False, 'error': 'Community ID required'}), 400

        # Get current user's type to determine which songs they should see
        user_id = get_current_user_id()
        user = fetch_one('users', 'user_id, user_type', user_id=user_id)

        if user:
            current_user_type = user.get('user_type', '')
        else:
            current_user_type = ''

        # Determine filter: show songs from the OPPOSITE generation
        # If wheel param is specified, use that; otherwise auto-detect from user type
        if wheel:
            filter_type = wheel
        elif current_user_type == 'senior':
            filter_type = 'youth'
        elif current_user_type == 'youth':
            filter_type = 'senior'
        else:
            filter_type = None  # Show all if type is unknown

        songs = get_songs_from_channel(community_id, user_type_filter=filter_type)

        if not songs:
            # Fallback: try all songs if no filtered songs found
            songs = get_songs_from_channel(community_id, user_type_filter=None)

        if not songs:
            return jsonify({
                'success': False,
                'error': 'No songs found in the recommendations channel. Try adding some songs first!'
            }), 404

        selected_song = random.choice(songs)

        return jsonify({
            'success': True,
            'song': selected_song,
            'allSongs': songs,
            'filterType': filter_type
        })

    except Exception as e:
        print(f"Error in spin_wheel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@jukebox_bp.route('/api/rate', methods=['POST'])
@login_required
def rate_song():
    """
    Submit a rating for a song.
    Posts the rating to the dedicated 'song-ratings' channel (not song-recommendations).
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
        
        supabase = get_supabase()
        
        # Find the dedicated 'song-ratings' channel
        ratings_channel = supabase.table('community_channels').select('*').eq(
            'community_id', community_id
        ).ilike('name', '%song-rating%').execute()
        
        # If it doesn't exist, create it automatically
        if not ratings_channel.data:
            try:
                new_chan = supabase.table('community_channels').insert({
                    'community_id': community_id,
                    'name': 'song-ratings',
                    'is_announcement': False,
                    'created_by': user_id
                }).execute()
                ratings_channel_id = new_chan.data[0]['channel_id'] if new_chan.data else None
            except Exception as ce:
                print(f"Warning: Could not create song-ratings channel: {ce}")
                ratings_channel_id = None
        else:
            ratings_channel_id = ratings_channel.data[0]['channel_id']
        
        if ratings_channel_id:
            # Create star rating display
            stars = '⭐' * rating
            rating_message = f"🎵 {username} rated \"{song_title}\" {stars} ({rating}/5) via Generational Jukebox!"
            
            # Post rating to the song-ratings channel
            supabase.table('community_messages').insert({
                'channel_id': ratings_channel_id,
                'user_id': user_id,
                'content': rating_message,
                'created_at': datetime.now().isoformat()
            }).execute()
        
        return jsonify({
            'success': True,
            'message': 'Rating submitted and posted to song-ratings channel!'
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
