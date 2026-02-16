"""
Debug script to check jukebox songs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase
from models.jukebox import get_songs_from_channel, extract_song_info

supabase = get_supabase()

# Check Musicly community
print("="*60)
print("CHECKING MUSICLY COMMUNITY")
print("="*60)
musicly = supabase.table('communities').select('*').eq('name', 'Musicly').execute()
if musicly.data:
    community_id = musicly.data[0]['community_id']
    print(f"✅ Found Musicly (ID: {community_id})")
else:
    print("❌ Musicly not found!")
    exit()

# Check channels
print("\n" + "="*60)
print("CHANNELS IN MUSICLY")
print("="*60)
channels = supabase.table('community_channels').select('*').eq('community_id', community_id).execute()
for ch in channels.data:
    print(f"  - Channel ID {ch['channel_id']}: {ch['name']}")

# Check song-recommendations channel specifically
print("\n" + "="*60)
print("CHECKING SONG-RECOMMENDATIONS CHANNEL")
print("="*60)
song_channel = supabase.table('community_channels').select('*').eq(
    'community_id', community_id
).ilike('name', '%song%recommend%').execute()

if song_channel.data:
    channel_id = song_channel.data[0]['channel_id']
    channel_name = song_channel.data[0]['name']
    print(f"✅ Found channel: '{channel_name}' (ID: {channel_id})")
    
    # Check messages in this channel
    messages = supabase.table('community_messages').select('*').eq(
        'channel_id', channel_id
    ).execute()
    
    print(f"\n📨 Total messages in channel: {len(messages.data)}")
    
    if messages.data:
        print("\nFirst few messages:")
        for i, msg in enumerate(messages.data[:3]):
            print(f"\n--- Message {i+1} ---")
            print(f"Content: {msg['content'][:100]}...")
            print(f"User ID: {msg['user_id']}")
            
            # Test parser
            song_info = extract_song_info(msg['content'])
            if song_info:
                print(f"✅ Parsed: {song_info.get('title')} by {song_info.get('artist')}")
            else:
                print("❌ Failed to parse")
    else:
        print("⚠️ No messages found in channel!")
        
else:
    print("❌ song-recommendations channel not found!")

# Test the get_songs_from_channel function
print("\n" + "="*60)
print("TESTING get_songs_from_channel()")
print("="*60)
songs = get_songs_from_channel(community_id)
print(f"Songs returned: {len(songs)}")
if songs:
    for song in songs:
        print(f"  - {song['title']} by {song['artist']} ({song['year']})")
else:
    print("⚠️ No songs returned by function!")

print("\n" + "="*60)
