-- Add streak tracking to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS sol_streak INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_sol_date DATE;

-- Ensure coins table exists and has entries for users
CREATE TABLE IF NOT EXISTS coins (
    user_id INTEGER PRIMARY KEY,
    total_coins INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Initialize coins for any missing users
INSERT INTO coins (user_id, total_coins)
SELECT user_id, 0 FROM users
ON CONFLICT (user_id) DO NOTHING;
