"""
Seed script to populate Supabase with sample data for testing
Run with: python database/seed_supabase.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase, insert, fetch_all


def seed_users():
    """Add sample users."""
    supabase = get_supabase()
    
    users = [
        {'username': 'Jeremy', 'email': 'jeremy@example.com', 'password_hash': 'hash123', 'user_type': 'youth'},
        {'username': 'Mdm Lim', 'email': 'mdmlim@example.com', 'password_hash': 'hash123', 'user_type': 'senior'},
        {'username': 'Uncle Ben', 'email': 'unclebento@example.com', 'password_hash': 'hash123', 'user_type': 'senior'},
        {'username': 'Tyler Joseph', 'email': 'tyler@example.com', 'password_hash': 'hash123', 'user_type': 'youth'},
    ]
    
    for user in users:
        try:
            result = insert('users', user)
            if result:
                print(f"✅ Created user: {user['username']}")
            else:
                print(f"⚠️ User may already exist: {user['username']}")
        except Exception as e:
            print(f"⚠️ Skipping {user['username']}: {e}")


def seed_messages():
    """Add sample messages."""
    # Get user IDs
    users = fetch_all('users')
    user_map = {u['username']: u['user_id'] for u in users}
    
    if not user_map:
        print("❌ No users found. Run seed_users() first.")
        return
    
    jeremy_id = user_map.get('Jeremy')
    mdm_lim_id = user_map.get('Mdm Lim')
    uncle_ben_id = user_map.get('Uncle Ben')
    tyler_id = user_map.get('Tyler Joseph')
    
    messages = [
        # Jeremy <-> Mdm Lim
        (mdm_lim_id, jeremy_id, "Hello Jeremy! How are you today?"),
        (jeremy_id, mdm_lim_id, "Hi Mdm Lim! I'm doing great, thank you!"),
        (mdm_lim_id, jeremy_id, "I think I'm gonna be okay."),
        (jeremy_id, mdm_lim_id, "Glad to hear that!"),
        
        # Jeremy <-> Uncle Ben
        (uncle_ben_id, jeremy_id, "Good morning! How are you?"),
        (jeremy_id, uncle_ben_id, "I'm great, Uncle Ben! How about you?"),
        
        # Jeremy <-> Tyler
        (tyler_id, jeremy_id, "Hey! Are you coming to the event?"),
        (jeremy_id, tyler_id, "Yes! I'll be there at 2pm"),
    ]
    
    for sender_id, receiver_id, content in messages:
        if sender_id and receiver_id:
            try:
                result = insert('messages', {
                    'sender_id': sender_id,
                    'receiver_id': receiver_id,
                    'content': content
                })
                if result:
                    print(f"✅ Message sent: {content[:30]}...")
            except Exception as e:
                print(f"⚠️ Error: {e}")


def main():
    print("🚀 Seeding Supabase database...")
    print("\n📦 Creating users...")
    seed_users()
    print("\n💬 Creating messages...")
    seed_messages()
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
