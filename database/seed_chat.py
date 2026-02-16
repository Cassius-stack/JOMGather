"""
Seed script to populate the database with sample chat data for testing
Run with: python database/seed_chat.py
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def seed_chat_data():
    """Add sample users and messages for testing chat."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Insert sample users if they don't exist
    users = [
        (1, 'Jeremy', 'jeremy@example.com', 'hash123', 'youth'),
        (2, 'Mdm Lim', 'mdmlim@example.com', 'hash123', 'senior'),
        (3, 'Uncle Ben', 'unclebento@example.com', 'hash123', 'senior'),
        (4, 'Tyler Joseph', 'tyler@example.com', 'hash123', 'youth'),
    ]
    
    for user in users:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, email, password_hash, user_type)
                VALUES (?, ?, ?, ?, ?)
            ''', user)
        except sqlite3.IntegrityError:
            pass
    
    # Insert sample messages
    messages = [
        # Conversation with Mdm Lim (user_id 2)
        (2, 1, "Hello Jeremy! How are you today?"),
        (1, 2, "Hi Mdm Lim! I'm doing great, thank you!"),
        (2, 1, "I think I'm gonna be okay."),
        (1, 2, "Glad to hear that!"),
        (1, 2, "Let's try today's challenge"),
        
        # Conversation with Uncle Ben (user_id 3)
        (3, 1, "Good morning! How are you today?"),
        (1, 3, "I'm doing great, Uncle Ben! How about you?"),
        (3, 1, "I loved the way you explained the phone settings yesterday."),
        (1, 3, "Happy to help anytime! 😊"),
        
        # Conversation with Tyler (user_id 4)
        (4, 1, "Hey! Are you coming to the community event?"),
        (1, 4, "Yes! I'll be there at 2pm"),
        (4, 1, "Maybe overcompensate?"),
        (1, 4, "Haha, I'll bring extra snacks just in case!"),
    ]
    
    # Clear existing messages first for clean seed
    cursor.execute('DELETE FROM messages')
    
    for msg in messages:
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, content)
            VALUES (?, ?, ?)
        ''', msg)
    
    conn.commit()
    conn.close()
    print("✅ Chat data seeded successfully!")
    print(f"   - Created {len(users)} users")
    print(f"   - Created {len(messages)} messages")

if __name__ == '__main__':
    seed_chat_data()

