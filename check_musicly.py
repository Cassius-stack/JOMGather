"""
Quick diagnostic + fix for jukebox "no songs" issue.
Run with: python check_musicly.py
"""

import os
import sys

# Add parent directory to path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from datetime import datetime

# Load from environment or config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set in environment or .env file!")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 CHECKING MUSICLY STATUS...\n")

# Step 1: Check if Musicly exists
print("1️⃣  Checking for Musicly community...")
musicly = supabase.table('communities').select('*').eq('name', 'Musicly').execute()

if not musicly.data:
    print("   ❌ Musicly doesn't exist!")
    print("   Run the SQL setup script first!")
    sys.exit(1)

musicly_id = musicly.data[0]['community_id']
print(f"   ✅ Musicly exists with ID: {musicly_id}")

# Step 2: Check channels
print("\n2️⃣  Checking channels...")
channels = supabase.table('community_channels').select('*').eq('community_id', musicly_id).execute()

song_channel = None
for ch in channels.data:
    print(f"   📁 {ch['name']} (ID: {ch['channel_id']})")
    if ch['name'] == 'song-recommendations':
        song_channel = ch

if not song_channel:
    print("   ❌ song-recommendations channel not found!")
    sys.exit(1)

song_channel_id = song_channel['channel_id']
print(f"   ✅ song-recommendations channel ID: {song_channel_id}")

# Step 3: Check messages
print("\n3️⃣  Checking for song messages...")
messages = supabase.table('community_messages').select('*').eq('channel_id', song_channel_id).execute()

print(f"   📊 Found {len(messages.data)} messages in channel")

if len(messages.data) > 0:
    print("\n   📜 Sample messages:")
    for i, msg in enumerate(messages.data[:3], 1):
        preview = msg['content'][:60].replace('\n', ' ')
        print(f"   {i}. {preview}...")

# Step 4: Check users
print("\n4️⃣  Checking for users...")
users = supabase.table('users').select('user_id, username').execute()
print(f"   👥 Found {len(users.data)} users")

if len(users.data) == 0:
    print("   ❌ No users! Create a user account first!")
    sys.exit(1)

first_user = users.data[0]
print(f"   ✅ First user: {first_user['username']} (ID: {first_user['user_id']})")

# Step 5: Offer to add songs
print("\n" + "="*60)
print("📊 SUMMARY")
print("="*60)
print(f"✅ Musicly ID: {musicly_id}")
print(f"✅ Song Channel ID: {song_channel_id}")
print(f"✅ Messages in channel: {len(messages.data)}")
print(f"✅ Users in system: {len(users.data)}")

if len(messages.data) == 0:
    print("\n" + "="*60)
    print("❌ PROBLEM: No songs in song-recommendations!")
    print("="*60)
    print("\nWould you like to add 8 sample songs? (y/n): ", end='')
    
    answer = input().strip().lower()
    
    if answer == 'y':
        print("\n5️⃣  Adding 8 sample songs...")
        
        songs = [
            ("Imagine", "John Lennon", "1971", "A beautiful vision of peace"),
            ("Bohemian Rhapsody", "Queen", "1975", "Epic rock opera masterpiece"),
            ("Hotel California", "Eagles", "1977", "Legendary guitar solo"),
            ("Billie Jean", "Michael Jackson", "1982", "Iconic bassline!"),
            ("Blinding Lights", "The Weeknd", "2020", "Addictive synth-wave beat"),
            ("As It Was", "Harry Styles", "2022", "Catchy and emotional"),
            ("Anti-Hero", "Taylor Swift", "2022", "Honest self-reflection"),
            ("Flowers", "Miley Cyrus", "2023", "Empowering anthem!"),
        ]
        
        for title, artist, year, reason in songs:
            content = f"""Song Name: {title}
Artist: {artist}
Year Released: {year}
Why they like this song: {reason}"""
            
            supabase.table('community_messages').insert({
               'channel_id': song_channel_id,
                'user_id': first_user['user_id'],
                'content': content,
                'created_at': datetime.now().isoformat()
            }).execute()
            
            print(f"   ✅ {title} - {artist}")
        
        print("\n🎉 SUCCESS! 8 songs added!")
        print("\n📝 NEXT STEPS:")
        print("1. Go to your jukebox page")
        print("2. Refresh (F5)")
        print("3. Click 'SPIN THE WHEEL!'")
        print("4. Songs should now appear! 🎵")
    else:
        print("\nOkay! Add songs manually in the song-recommendations channel.")
else:
    print("\n✅ Looks good! Songs exist in the database.")
    print("\nIf jukebox still shows 'no songs', check:")
    print(f"1. The jukebox template uses community_id = {musicly_id}")
    print("2. Refresh the jukebox page after changes")
