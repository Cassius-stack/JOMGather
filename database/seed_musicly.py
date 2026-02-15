"""
Enhanced Seed Script for JOMGather
Creates Musicly community and automatically adds all users to it
Run with: python database/seed_musicly.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase, insert, fetch_all
from datetime import datetime


def create_musicly_community():
    """Create the default Musicly community that all users auto-join."""
    supabase = get_supabase()
    
    # Check if Musicly community already exists
    existing = supabase.table('communities').select('*').eq('name', 'Musicly').execute()
    
    if existing.data:
        print(f"✅ Musicly community already exists (ID: {existing.data[0]['community_id']})")
        return existing.data[0]
    
    # Get first user to be creator (or create system user)
    users = fetch_all('users')
    if not users:
        print("❌ No users found. Please create users first.")
        return None
    
    creator_id = users[0]['user_id']
    print(f"📝 Using user {creator_id} as creator")
    
    # Create Musicly community
    community_data = {
        'name': 'Musicly',
        'description': 'The default music community for all JOMGather users! Share songs, discover new tunes, and connect through music. 🎵',
        'category': 'music',
        'created_by': creator_id
    }
    
    try:
        community = insert('communities', community_data)
        print(f"✅ Created Musicly community (ID: {community['community_id']})")
        
        # Set creator as admin
        insert('community_roles', {
            'community_id': community['community_id'],
            'user_id': creator_id,
            'role': 'admin'
        })
        
        return community
    except Exception as e:
        print(f"❌ Error creating community: {e}")
        return None


def add_all_users_to_musicly(community_id):
    """Add all existing users to Musicly community."""
    supabase = get_supabase()
    
    users = fetch_all('users')
    print(f"\n📦 Adding {len(users)} users to Musicly...")
    
    for user in users:
        user_id = user['user_id']
        
        # Check if already a member
        existing = supabase.table('community_members').select('*').eq('community_id', community_id).eq('user_id', user_id).execute()
        
        if not existing.data:
            try:
                insert('community_members', {
                    'community_id': community_id,
                    'user_id': user_id
                })
                print(f"  ✅ Added user {user['username']} to Musicly")
            except Exception as e:
                print(f"  ⚠️ Could not add {user['username']}: {e}")
        else:
            print(f"  ℹ️ User {user['username']} already in Musicly")


def create_default_channels(community_id, creator_id):
    """Create default channels for Musicly community."""
    supabase = get_supabase()
    
    channels = [
        {'name': 'announcements', 'is_announcement': True, 'description': '📣 Official announcements'},
        {'name': 'general', 'is_announcement': False, 'description': '💬 General music chat'},
        {'name': 'song-recommendations', 'is_announcement': False, 'description': '🎵 Share your favorite songs'},
        {'name': 'jukebox', 'is_announcement': False, 'description': '🎰 Generational Jukebox channel'},
    ]
    
    print(f"\n📂 Creating channels for Musicly...")
    
    for channel_data in channels:
        # Check if channel already exists
        existing = supabase.table('community_channels').select('*').eq('community_id', community_id).eq('name', channel_data['name']).execute()
        
        if not existing.data:
            try:
                channel = insert('community_channels', {
                    'community_id': community_id,
                    'name': channel_data['name'],
                    'is_announcement': channel_data['is_announcement'],
                    'created_by': creator_id
                })
                print(f"  ✅ Created channel: {channel_data['name']}")
                
                # Add welcome message to some channels
                if channel_data['name'] == 'general':
                    insert('community_messages', {
                        'channel_id': channel['channel_id'],
                        'user_id': creator_id,
                        'content': '🎵 Welcome to Musicly! Share your favorite songs and discover new music!'
                    })
                elif channel_data['name'] == 'song-recommendations':
                    insert('community_messages', {
                        'channel_id': channel['channel_id'],
                        'user_id': creator_id,
                        'content': '🎼 Post your favorite songs here! Include YouTube or Spotify links.'
                    })
                    # Add sample song recommendations
                    sample_songs = [
                        "Check out this classic: What a Wonderful World by Louis Armstrong 🎺",
                        "Can't stop listening to Blinding Lights by The Weeknd! 🌟",
                        "Bohemian Rhapsody is a masterpiece! 🎸",
                    ]
                    for song in sample_songs:
                        insert('community_messages', {
                            'channel_id': channel['channel_id'],
                            'user_id': creator_id,
                            'content': song
                        })
                elif channel_data['name'] == 'jukebox':
                    insert('community_messages', {
                        'channel_id': channel['channel_id'],
                        'user_id': creator_id,
                        'content': '🎰 Welcome to the Generational Jukebox! Spin the wheel and rate songs together!'
                    })
                    
            except Exception as e:
                print(f"  ⚠️ Could not create {channel_data['name']}: {e}")
        else:
            print(f"  ℹ️ Channel '{channel_data['name']}' already exists")


def main():
    print("🚀 Setting up Musicly - The Default Community\n")
    print("=" * 60)
    
    # Step 1: Create Musicly community
    print("\n📝 STEP 1: Creating Musicly Community")
    community = create_musicly_community()
    
    if not community:
        print("\n❌ Failed to create Musicly community. Exiting.")
        return
    
    community_id = community['community_id']
    creator_id = community['created_by']
    
    # Step 2: Add all users to Musicly
    print("\n📝 STEP 2: Adding All Users to Musicly")
    add_all_users_to_musicly(community_id)
    
    # Step 3: Create default channels
    print("\n📝 STEP 3: Creating Default Channels")
    create_default_channels(community_id, creator_id)
    
    print("\n" + "=" * 60)
    print("✅ MUSICLY SETUP COMPLETE!")
    print(f"   Community ID: {community_id}")
    print(f"   All users have been added to Musicly")
    print(f"   Default channels created")
    print("=" * 60)


if __name__ == '__main__':
    main()
