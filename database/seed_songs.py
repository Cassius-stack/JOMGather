"""
Seed Sample Songs for Jukebox
Adds sample songs from youth and seniors to the song-recommendations channel
Run with: python database/seed_songs.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase, fetch_one
from datetime import datetime


def seed_songs():
    """Add sample songs to the song-recommendations channel."""
    supabase = get_supabase()
    
    # Get Musicly community
    musicly = supabase.table('communities').select('*').eq('name', 'Musicly').execute()
    if not musicly.data:
        print("❌ Musicly community not found. Run seed_musicly.py first!")
        return
    
    community_id = musicly.data[0]['community_id']
    print(f"✅ Found Musicly community (ID: {community_id})")
    
    # Get song-recommendations channel
    channel = supabase.table('community_channels').select('*').eq(
        'community_id', community_id
    ).ilike('name', '%song%recommend%').execute()
    
    if not channel.data:
        print("❌ song-recommendations channel not found!")
        return
    
    channel_id = channel.data[0]['channel_id']
    print(f"✅ Found song-recommendations channel (ID: {channel_id})")
    
    # Get any two users from the database for demonstration
    all_users = supabase.table('users').select('*').limit(2).execute()
    
    if not all_users.data or len(all_users.data) < 2:
        print("❌ Need at least 2 users in the database!")
        print("   Using the same user for both types...")
        if not all_users.data:
            return
        user1 = all_users.data[0]
        user2 = all_users.data[0]
    else:
        user1 = all_users.data[0]
        user2 = all_users.data[1]
    
    print(f"✅ Using {user1['username']} for classic songs (1900s era)")
    print(f"✅ Using {user2['username']} for modern songs (2000s era)")
    
    # Classic songs from 1900s era
    classic_songs = [
        {
            'title': 'What a Wonderful World',
            'artist': 'Louis Armstrong',
            'year': '1967',
            'reason': 'This song always brings a smile to my face and reminds me to appreciate the simple beauties in life.'
        },
        {
            'title': 'Bohemian Rhapsody',
            'artist': 'Queen',
            'year': '1975',
            'reason': 'A true masterpiece that never gets old. The vocals and composition are absolutely magical!'
        },
        {
            'title': 'Stand By Me',
            'artist': 'Ben E. King',
            'year': '1961',
            'reason': 'This was playing when I met my spouse. It reminds me that we are never truly alone.'
        },
        {
            'title': 'My Way',
            'artist': 'Frank Sinatra',
            'year': '1969',
            'reason': 'A timeless classic about living life on your own terms. The lyrics are so powerful!'
        }
    ]
    
    # Modern songs from 2000s era
    modern_songs = [
        {
            'title': 'Blinding Lights',
            'artist': 'The Weeknd',
            'year': '2019',
            'reason': 'The beat is absolutely infectious and it makes me want to dance every time I hear it!'
        },
        {
            'title': 'Good 4 U',
            'artist': 'Olivia Rodrigo',
            'year': '2021',
            'reason': 'The raw emotion and energy in this song is amazing. Perfect for when you need to let it all out!'
        },
        {
            'title': 'Levitating',
            'artist': 'Dua Lipa',
            'year': '2020',
            'reason': 'This song has the perfect disco-pop vibe. It never fails to put me in a good mood!'
        },
        {
            'title': 'Circles',
            'artist': 'Post Malone',
            'year': '2019',
            'reason': 'Super catchy and relatable. I can listen to this on repeat all day!'
        }
    ]
    
    print("\n📀 Adding classic songs (1900s era)...")
    for song in classic_songs:
        content = f"""Song Name: {song['title']}
Artist: {song['artist']}
Year Released: {song['year']}
Why they like this song: {song['reason']}"""
        
        try:
            supabase.table('community_messages').insert({
                'channel_id': channel_id,
                'user_id': user1['user_id'],
                'content': content,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"  ✅ Added: {song['title']} by {song['artist']} ({song['year']})")
        except Exception as e:
            print(f"  ⚠️ Error adding {song['title']}: {e}")
    
    print("\n🎵 Adding modern songs (2000s era)...")
    for song in modern_songs:
        content = f"""Song Name: {song['title']}
Artist: {song['artist']}
Year Released: {song['year']}
Why they like this song: {song['reason']}"""
        
        try:
            supabase.table('community_messages').insert({
                'channel_id': channel_id,
                'user_id': user2['user_id'],
                'content': content,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"  ✅ Added: {song['title']} by {song['artist']} ({song['year']})")
        except Exception as e:
            print(f"  ⚠️ Error adding {song['title']}: {e}")
    
    print("\n" + "="*60)
    print("✅ SAMPLE SONGS ADDED!")
    print(f"   - {len(classic_songs)} classic songs from 1960s-1970s era")
    print(f"   - {len(modern_songs)} modern songs from 2019-2021 era")
    print("="*60)
    print("\n🎰 Now go to the Jukebox and spin the wheel!")
    print("   All songs are available for demonstration!")


if __name__ == '__main__':
    seed_songs()
