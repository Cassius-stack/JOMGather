"""
Seed script: Creates a 'song-ratings' channel in the Musicly community
if it doesn't already exist. Run once after deploying the jukebox rating fix.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase

def seed_song_ratings_channel():
    supabase = get_supabase()

    # Find Musicly
    musicly = supabase.table('communities').select('community_id, created_by').eq('name', 'Musicly').execute()
    if not musicly.data:
        print("❌ Musicly community not found. Skipping.")
        return

    for community in musicly.data:
        community_id = community['community_id']
        created_by = community.get('created_by', 1)

        # Check if song-ratings already exists
        existing = supabase.table('community_channels').select('channel_id, name').eq(
            'community_id', community_id
        ).ilike('name', '%song-rating%').execute()

        if existing.data:
            print(f"✅ 'song-ratings' channel already exists in Musicly (community {community_id}): {existing.data[0]['name']}")
            continue

        # Create it
        result = supabase.table('community_channels').insert({
            'community_id': community_id,
            'name': 'song-ratings',
            'is_announcement': False,
            'created_by': created_by
        }).execute()

        if result.data:
            print(f"✅ Created 'song-ratings' channel in Musicly (community {community_id}), channel_id={result.data[0]['channel_id']}")
        else:
            print(f"⚠️  Insert returned no data. Check Supabase dashboard for community {community_id}.")

if __name__ == '__main__':
    seed_song_ratings_channel()
    print("Done.")
