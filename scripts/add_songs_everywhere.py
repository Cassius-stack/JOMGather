"""
Add songs to the ACTUAL song-recommendations channel in use.
This script finds ALL song-recommendations channels and adds songs to each.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase

def add_songs_to_all_channels():
    """Add 8 default songs to ALL song-recommendations channels."""
    supabase = get_supabase()
    
    print("🎵 Finding ALL song-recommendations channels...")
    
    # Find ALL song-recommendations channels
    channels = supabase.table('community_channels').select(
        'channel_id, community_id, name'
    ).eq('name', 'song-recommendations').execute()
    
    if not channels.data:
        print("❌ No song-recommendations channels found!")
        return False
    
    print(f"✅ Found {len(channels.data)} song-recommendations channel(s)")
    
    # Get first user
    users = supabase.table('users').select('user_id').limit(1).execute()
    if not users.data:
        print("❌ No users found!")
        return False
    
    user_id = users.data[0]['user_id']
    
    # Default songs
    default_songs = [
        ("Imagine", "John Lennon", "1971", "A beautiful vision of peace"),
        ("Bohemian Rhapsody", "Queen", "1975", "Epic rock opera masterpiece"),
        ("Hotel California", "Eagles", "1977", "Legendary guitar solo"),
        ("Billie Jean", "Michael Jackson", "1982", "Iconic bassline"),
        ("Blinding Lights", "The Weeknd", "2020", "Addictive synth-wave beat"),
        ("As It Was", "Harry Styles", "2022", "Catchy and emotional"),
        ("Anti-Hero", "Taylor Swift", "2022", "Honest self-reflection"),
        ("Flowers", "Miley Cyrus", "2023", "Empowering anthem"),
    ]
    
    # Add songs to EACH channel
    for channel in channels.data:
        channel_id = channel['channel_id']
        community_id = channel['community_id']
        
        print(f"\n📁 Channel {channel_id} (Community {community_id}):")
        added = 0
        
        for title, artist, year, reason in default_songs:
            # Check if exists
            existing = supabase.table('community_messages').select('message_id').eq(
                'channel_id', channel_id
            ).ilike('content', f'%{title}%').ilike('content', f'%{artist}%').execute()
            
            if existing.data:
                print(f"   ⏭️  {title} (exists)")
                continue
            
            # Add song
            content = f"""Song Name: {title}
Artist: {artist}
Year Released: {year}
Why they like this song: {reason}"""
            
            try:
                supabase.table('community_messages').insert({
                    'channel_id': channel_id,
                    'user_id': user_id,
                    'content': content,
                    'created_at': datetime.now().isoformat()
                }).execute()
                print(f"   ✅ {title}")
                added += 1
            except Exception as e:
                print(f"   ❌ {title}: {e}")
        
        print(f"   📊 Added {added} songs to this channel")
    
    print(f"\n🎉 Done! Refresh jukebox to see songs!")
    return True

if __name__ == '__main__':
    add_songs_to_all_channels()
