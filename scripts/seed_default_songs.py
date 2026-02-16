"""
Seed default songs for Musicly jukebox.
Run this script to add 8 default songs to the jukebox.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase

def seed_default_songs():
    """Add 8 default songs to Musicly's song-recommendations channel."""
    supabase = get_supabase()
    
    print("🎵 Seeding default songs for Musicly jukebox...")
    
    # Find Musicly community
    musicly = supabase.table('communities').select('community_id').eq('name', 'Musicly').execute()
    if not musicly.data:
        print("❌ Error: Musicly community not found!")
        return False
    
    musicly_id = musicly.data[0]['community_id']
    print(f"✅ Found Musicly (ID: {musicly_id})")
    
    # Find song-recommendations channel
    channel = supabase.table('community_channels').select('channel_id').eq(
        'community_id', musicly_id
    ).eq('name', 'song-recommendations').execute()
    
    if not channel.data:
        print("❌ Error: song-recommendations channel not found!")
        return False
    
    channel_id = channel.data[0]['channel_id']
    print(f"✅ Found song-recommendations (ID: {channel_id})")
    
    # Get first user (or create a system user)
    users = supabase.table('users').select('user_id').limit(1).execute()
    if not users.data:
        print("❌ Error: No users found! Create a user first.")
        return False
    
    user_id = users.data[0]['user_id']
    print(f"✅ Using user ID: {user_id}")
    
    # Default songs: 4 classics + 4 modern
    default_songs = [
        # Classics
        ("Imagine", "John Lennon", "1971", "A beautiful vision of peace and unity"),
        ("Bohemian Rhapsody", "Queen", "1975", "Epic rock opera masterpiece with incredible vocals"),
        ("Hotel California", "Eagles", "1977", "Legendary guitar solo and mysterious storytelling"),
        ("Billie Jean", "Michael Jackson", "1982", "Iconic bassline and the King of Pop at his best"),
        
        # Modern hits
        ("Blinding Lights", "The Weeknd", "2020", "Addictive synth-wave beat that's pure nostalgia"),
        ("As It Was", "Harry Styles", "2022", "Catchy melody with emotional depth about change"),
        ("Anti-Hero", "Taylor Swift", "2022", "Honest self-reflection everyone can relate to"),
        ("Flowers", "Miley Cyrus", "2023", "Empowering anthem about self-love and independence"),
    ]
    
    print(f"\n📝 Adding {len(default_songs)} default songs...")
    added = 0
    
    for title, artist, year, reason in default_songs:
        # Check if song already exists
        existing = supabase.table('community_messages').select('message_id').eq(
            'channel_id', channel_id
        ).ilike('content', f'%{title}%').ilike('content', f'%{artist}%').execute()
        
        if existing.data:
            print(f"   ⏭️  Skipped: {title} (already exists)")
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
            print(f"   ✅ Added: {title} - {artist}")
            added += 1
        except Exception as e:
            print(f"   ❌ Failed: {title} - {e}")
    
    print(f"\n🎉 Done! Added {added} new songs.")
    print("   Refresh your jukebox page to see them!")
    return True

if __name__ == '__main__':
    seed_default_songs()
