"""
Seed script to add sample songs to Musicly community.
Run this with: python scripts/seed_songs.py
"""

from utils.supabase_db import get_supabase, fetch_one
from datetime import datetime

def seed_musicly_songs():
    """Add 8 sample songs to Musicly's song-recommendations channel."""
    supabase = get_supabase()
    
    print("🎵 Starting song seeding...\n")
    
    # Step 1: Find Musicly community
    print("1️⃣  Finding Musicly community...")
    musicly = supabase.table('communities').select('*').eq('name', 'Musicly').execute()
    
    if not musicly.data:
        print("   ❌ ERROR: Musicly community doesn't exist!")
        print("   Run the SQL setup first!")
        return False
    
    community_id = musicly.data[0]['community_id']
    print(f"   ✅ Found Musicly (ID: {community_id})")
    
    # Step 2: Find song-recommendations channel
    print("\n2️⃣  Finding song-recommendations channel...")
    channel = supabase.table('community_channels').select('*').eq(
        'community_id', community_id
    ).eq('name', 'song-recommendations').execute()
    
    if not channel.data:
        print("   ❌ ERROR: song-recommendations channel doesn't exist!")
        return False
    
    channel_id = channel.data[0]['channel_id']
    print(f"   ✅ Found channel (ID: {channel_id})")
    
    # Step 3: Get first user
    print("\n3️⃣  Finding a user to post songs...")
    users = supabase.table('users').select('user_id, username').limit(1).execute()
    
    if not users.data:
        print("   ❌ ERROR: No users exist! Create a user account first!")
        return False
    
    user_id = users.data[0]['user_id']
    username = users.data[0]['username']
    print(f"   ✅ Using user: {username} (ID: {user_id})")
    
    # Step 4: Check existing songs
    print("\n4️⃣  Checking existing songs...")
    existing = supabase.table('community_messages').select('*').eq('channel_id', channel_id).execute()
    print(f"   ℹ️  Found {len(existing.data)} existing messages")
    
    # Step 5: Add sample songs
    print("\n5️⃣  Adding 8 sample songs...")
    
    songs = [
        {
            'title': 'Blinding Lights',
            'artist': 'The Weeknd',
            'year': 2019,
            'reason': 'Amazing synth-wave beat!'
        },
        {
            'title': 'Bohemian Rhapsody',
            'artist': 'Queen',
            'year': 1975,
            'reason': 'Timeless rock opera masterpiece'
        },
        {
            'title': 'Shape of You',
            'artist': 'Ed Sheeran',
            'year': 2017,
            'reason': 'Super catchy rhythm!'
        },
        {
            'title': 'Yesterday',
            'artist': 'The Beatles',
            'year': 1965,
            'reason': 'Beautiful and emotional'
        },
        {
            'title': 'Levitating',
            'artist': 'Dua Lipa',
            'year': 2020,
            'reason': 'Perfect disco-pop vibes!'
        },
        {
            'title': 'Hotel California',
            'artist': 'Eagles',
            'year': 1976,
            'reason': 'Legendary guitar solo'
        },
        {
            'title': 'Anti-Hero',
            'artist': 'Taylor Swift',
            'year': 2022,
            'reason': 'Honest and relatable'
        },
        {
            'title': 'Imagine',
            'artist': 'John Lennon',
            'year': 1971,
            'reason': 'Beautiful vision of peace'
        }
    ]
    
    added_count = 0
    for song in songs:
        content = f"""Song Name: {song['title']}
Artist: {song['artist']}
Year Released: {song['year']}
Why they like this song: {song['reason']}"""
        
        try:
            supabase.table('community_messages').insert({
                'channel_id': channel_id,
                'user_id': user_id,
                'content': content,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"   ✅ Added: {song['title']} - {song['artist']}")
            added_count += 1
        except Exception as e:
            print(f"   ❌ Failed to add {song['title']}: {e}")
    
    # Step 6: Verify
    print(f"\n6️⃣  Verification...")
    final = supabase.table('community_messages').select('*').eq('channel_id', channel_id).execute()
    print(f"   ✅ Total songs in channel: {len(final.data)}")
    print(f"   ✅ Songs added this run: {added_count}")
    
    print("\n🎉 DONE! Go to Jukebox and refresh the page!")
    return True

if __name__ == '__main__':
    seed_musicly_songs()
