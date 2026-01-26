"""
Jukebox Model - Song wheel feature for communities
Allows users to spin a wheel of song recommendations and rate them
"""

import re
from datetime import datetime
from utils.supabase_db import get_supabase, fetch_one, fetch_all


def extract_song_info(message_text):
    """
    Extract song information from a chat message.
    Parses YouTube, Spotify links or plain text song titles.
    
    Returns dict with: title, url, source (youtube/spotify/text)
    """
    # YouTube URL patterns
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)'
    ]
    
    # Spotify URL patterns
    spotify_patterns = [
        r'(?:https?://)?open\.spotify\.com/track/([a-zA-Z0-9]+)',
        r'(?:https?://)?spotify\.link/([a-zA-Z0-9]+)'
    ]
    
    # Check for YouTube links
    for pattern in youtube_patterns:
        match = re.search(pattern, message_text)
        if match:
            video_id = match.group(1)
            url = f'https://www.youtube.com/watch?v={video_id}'
            # Extract title from message (text before or after URL)
            title = re.sub(pattern, '', message_text).strip()
            if not title:
                title = f'YouTube Song #{video_id[:6]}'
            return {
                'title': title[:100],  # Limit title length
                'url': url,
                'source': 'youtube'
            }
    
    # Check for Spotify links
    for pattern in spotify_patterns:
        match = re.search(pattern, message_text)
        if match:
            track_id = match.group(1)
            url = f'https://open.spotify.com/track/{track_id}'
            title = re.sub(pattern, '', message_text).strip()
            if not title:
                title = f'Spotify Track #{track_id[:6]}'
            return {
                'title': title[:100],
                'url': url,
                'source': 'spotify'
            }
    
    # If no URL found, treat the whole message as a song title
    # Only if it looks like a song recommendation (not too long)
    if len(message_text) < 100 and message_text.strip():
        return {
            'title': message_text.strip(),
            'url': None,
            'source': 'text'
        }
    
    return None


def get_songs_from_channel(community_id, channel_name='song recommendations'):
    """
    Get all song recommendations from a specific channel.
    
    Returns list of song dicts with: id, title, url, source, userId, userName, timestamp
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
        if song_info:
            # Get user info
            user = fetch_one('users', 'user_id, username', user_id=msg['user_id'])
            songs.append({
                'id': msg['message_id'],
                'title': song_info['title'],
                'url': song_info['url'],
                'source': song_info['source'],
                'userId': msg['user_id'],
                'userName': user['username'] if user else 'Unknown',
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
