"""
Reward model - Coins, Items
"""
import sqlite3

# Database path
DB_PATH = 'database/jomgather.db'


def get_user_coins(user_id):
    """Get user's current coin balance."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT total_coins FROM coins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def add_coins(user_id, amount):
    """Add coins to user's balance."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO coins (user_id, total_coins)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET total_coins = total_coins + ?
    """, (user_id, amount, amount))
    conn.commit()
    conn.close()


def remove_coins(user_id, amount):
    """Remove coins from user's balance. Returns True if successful."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE coins SET total_coins = total_coins - ?
        WHERE user_id = ? AND total_coins >= ?
    """, (amount, user_id, amount))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success