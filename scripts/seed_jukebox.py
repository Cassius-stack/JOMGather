"""
Seed Jukebox Script
Creates the 'Music.ly' community and 'song recommendations' channel if they don't exist.
Adds sample song messages for testing.
"""

import sys
import os

# Add parent dir to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from utils.supabase_db import get_supabase
from datetime import datetime

app = create_app()

def seed_jukebox():
    with app.app_context():
        supabase = get_supabase()
        
        # 1. Check/Create Community
        community_name = "Music.ly"
        print(f"Checking for community: {community_name}")
        
        response = supabase.table('communities').select('*').ilike('name', community_name).execute()
        
        if response.data:
            community = response.data[0]
            print(f"Community found: {community['name']} (ID: {community['community_id']})")
        else:
            print("Creating Music.ly community...")
            # We need a creator ID. For now, try to get the first user
            users = supabase.table('users').select('user_id').limit(1).execute()
            if not users.data:
                print("Error: No users found in database to be the creator.")
                return
            
            creator_id = users.data[0]['user_id']
            
            new_comm_data = {
                'name': community_name,
                'description': 'A community for music lovers to share and discover tunes!',
                'created_by': creator_id,
                'is_public': True
            }
            
            res = supabase.table('communities').insert(new_comm_data).execute()
            community = res.data[0]
            print(f"Created community: {community['name']} (ID: {community['community_id']})")
            
            # Add creator as admin member
            supabase.table('community_members').insert({
                'community_id': community['community_id'],
                'user_id': creator_id,
                'role': 'admin'
            }).execute()

        community_id = community['community_id']

        # 2. Check/Create Channel
        channel_name = "song recommendations"
        print(f"Checking for channel: {channel_name}")
        
        c_res = supabase.table('community_channels').select('*').eq('community_id', community_id).ilike('name', f'%{channel_name}%').execute()
        
        if c_res.data:
            channel = c_res.data[0]
            print(f"Channel found: {channel['name']} (ID: {channel['channel_id']})")
        else:
            print("Creating channel...")
            # Find an admin to be the creator
            admins = supabase.table('community_members').select('user_id').eq('community_id', community_id).eq('role', 'admin').execute()
            creator_id = admins.data[0]['user_id'] if admins.data else community['created_by']
            
            new_chan_data = {
                'community_id': community_id,
                'name': channel_name,
                'is_announcement': False,
                'created_by': creator_id
            }
            
            res = supabase.table('community_channels').insert(new_chan_data).execute()
            channel = res.data[0]
            print(f"Created channel: {channel['name']} (ID: {channel['channel_id']})")

        # 3. Add Sample Songs if empty
        print("Checking for messages...")
        channel_id = channel['channel_id']
        msgs = supabase.table('community_messages').select('*').eq('channel_id', channel_id).execute()
        
        if len(msgs.data) < 3:
            print("Adding sample song messages...")
            # Get a user to post
            user_res = supabase.table('users').select('user_id').limit(1).execute()
            user_id = user_res.data[0]['user_id']
            
            samples = [
                "Check out this classic: https://www.youtube.com/watch?v=dQw4w9WgXcQ Never Gonna Give You Up",
                "I love this song for studying: https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=2e3f4g5h",
                "Bohemian Rhapsody is the best song ever! https://youtu.be/fJ9rUzIMcZQ",
                "Can't stop listening to Blinding Lights https://www.youtube.com/watch?v=4NRXx6U8ABQ"
            ]
            
            for content in samples:
                supabase.table('community_messages').insert({
                    'channel_id': channel_id,
                    'user_id': user_id,
                    'content': content
                }).execute()
            print("Added sample messages.")
        else:
            print(f"Channel already has {len(msgs.data)} messages.")

        print("\nSUCCESS! Jukebox setup complete.")
        print(f"Target Community ID: {community_id}")

if __name__ == "__main__":
    seed_jukebox()
