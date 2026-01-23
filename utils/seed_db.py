
import sqlite3
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from werkzeug.security import generate_password_hash

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_database():
    print("🌱 Seeding database...")
    
    # Path to schema
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'schema.sql')
    
    # 1. Initialize Schema (Reset DB)
    if os.path.exists(Config.DATABASE_PATH):
        os.remove(Config.DATABASE_PATH)
        print("   - Removed existing database.")
    
    conn = get_db_connection()
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    print("   - Schema initialized.")

    # 2. Create Users
    users = [
        ('jeremy', 'jeremy@example.com', 'password123', 'youth'),
        ('grandma_rose', 'rose@example.com', 'password123', 'senior'),
        ('uncle_ben', 'ben@example.com', 'password123', 'senior'),
        ('aunt_may', 'may@example.com', 'password123', 'senior'),
        ('sarah', 'sarah@example.com', 'password123', 'youth'),
        ('mdm_lim', 'lim@example.com', 'password123', 'senior')
    ]

    for username, email, password, user_type in users:
        conn.execute('INSERT INTO users (username, email, password_hash, user_type) VALUES (?, ?, ?, ?)',
                     (username, email, generate_password_hash(password), user_type))
    print(f"   - Created {len(users)} users.")

    # Get User IDs for profiles
    jeremy_id = conn.execute("SELECT user_id FROM users WHERE username = 'jeremy'").fetchone()['user_id']
    rose_id = conn.execute("SELECT user_id FROM users WHERE username = 'grandma_rose'").fetchone()['user_id']

    # 3. Create Profiles
    conn.execute('INSERT INTO profiles (user_id, bio, peak_hours) VALUES (?, ?, ?)',
                 (jeremy_id, "I love photography and stories!", "Mon-Fri 6pm-9pm"))
    conn.execute('INSERT INTO profiles (user_id, bio, peak_hours) VALUES (?, ?, ?)',
                 (rose_id, "Loving life in Bishan.", "Weekends 10am-4pm"))
    print("   - Created profiles.")

    # 4. Create Daily Prompt
    conn.execute("INSERT INTO sol_prompts (prompt_text, active_date) VALUES (?, date('now'))",
                 ("What is your favourite thing to do after school/work?",))
    print("   - Created daily prompt.")

    conn.commit()
    conn.close()
    print("✅ Database seeded successfully!")

if __name__ == "__main__":
    seed_database()
