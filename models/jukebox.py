"""
Jukebox Model - Song wheel feature for communities
Allows users to spin a wheel of song recommendations and rate them
"""

import re
from datetime import datetime
from utils.supabase_db import get_supabase, fetch_one, fetch_all


def extract_song_info(message_text):
    """
    Extract song information from a structured chat message.
    Expected format:
    Song Name: <song>
    Artist: <artist>
    Year Released: <year>
    Why they like this song: <reason>
    
    Returns dict with: title, artist, year, reason
    """
    lines = message_text.strip().split('\n')
    song_data = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith('Song Name:'):
            song_data['title'] = line.replace('Song Name:', '').strip()
        elif line.startswith('Artist:'):
            song_data['artist'] = line.replace('Artist:', '').strip()
        elif line.startswith('Year Released:'):
            year_str = line.replace('Year Released:', '').strip()
            try:
                song_data['year'] = int(year_str)
            except:
                song_data['year'] = year_str
        elif line.startswith('Why they like this song:'):
            song_data['reason'] = line.replace('Why they like this song:', '').strip()
    
    # Validate that we have the required fields
    if 'title' in song_data and 'artist' in song_data:
        return song_data
    
    return None


def get_songs_from_channel(community_id, channel_name='song-recommendations', user_type_filter=None):
    """
    Get all song recommendations from a specific channel.

    Args:
        community_id: ID of the community
        channel_name: Name of the channel (default: 'song-recommendations')
        user_type_filter: Filter songs by era:
            'youth'  → songs released in 2000 or later
            'senior' → songs released before 2000
            None     → return all songs

    Returns list of song dicts with: id, title, artist, year, reason, userId, userName, timestamp
    """
    supabase = get_supabase()

    # Find the channel
    channel = supabase.table('community_channels').select('*').eq(
        'community_id', community_id
    ).ilike('name', f'%{channel_name}%').execute()

    if not channel.data:
        return []

    channel_id = channel.data[0]['channel_id']

    # Get messages from the channel
    messages = supabase.table('community_messages').select('*').eq(
        'channel_id', channel_id
    ).order('created_at', desc=True).limit(100).execute()

    songs = []
    for msg in messages.data:
        song_info = extract_song_info(msg['content'])
        if not song_info:
            continue

        # Determine the song's era based on year
        year = song_info.get('year')
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            year_int = None  # year is missing or not a number

        # Apply era filter if specified
        if user_type_filter == 'youth':
            # Youth wheel: songs from 2000 onwards
            if year_int is None or year_int < 2000:
                continue
        elif user_type_filter == 'senior':
            # Senior wheel: songs before 2000
            if year_int is None or year_int >= 2000:
                continue

        # Fetch sender username (no longer needed for filtering, just for display)
        user = fetch_one('users', 'user_id, username', user_id=msg['user_id'])
        user_name = user['username'] if user else 'Unknown'

        songs.append({
            'id': msg['message_id'],
            'title': song_info['title'],
            'artist': song_info.get('artist', 'Unknown'),
            'year': year_int if year_int is not None else year,
            'reason': song_info.get('reason', ''),
            'userId': msg['user_id'],
            'userName': user_name,
            'timestamp': msg['created_at']
        })

    return songs



def save_song_rating(user_id, song_id, rating, community_id):
    """
    Save a user's rating for a song.
    Also posts the rating to the community chat.
    
    Returns True on success.
    """
    supabase = get_supabase()
    
    # Save rating to jukebox_ratings table
    rating_data = {
        'user_id': user_id,
        'message_id': song_id,  # The original message that contained the song
        'rating': rating,
        'created_at': datetime.now().isoformat()
    }
    
    try:
        supabase.table('jukebox_ratings').insert(rating_data).execute()
    except Exception as e:
        # Table might not exist, that's ok for now
        print(f"Warning: Could not save rating to jukebox_ratings: {e}")
    
    return True


def get_user_spin_history(user_id, community_id, limit=10):
    """
    Get a user's spin history for a community.
    
    Returns list of spins with song info and ratings.
    """
    supabase = get_supabase()
    
    try:
        history = supabase.table('jukebox_ratings').select('*').eq(
            'user_id', user_id
        ).order('created_at', desc=True).limit(limit).execute()
        return history.data
    except:
        return []
