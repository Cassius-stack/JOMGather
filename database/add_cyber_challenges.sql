-- Cyber Challenges Table for JOMGather
-- Run this in Supabase SQL Editor
CREATE TABLE IF NOT EXISTS cyber_challenges (
    challenge_id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(message_id) ON DELETE CASCADE,
    scenario_id INTEGER NOT NULL,
    user1_id INTEGER REFERENCES users(user_id),
    user2_id INTEGER REFERENCES users(user_id),
    user1_answer VARCHAR(10),
    -- 'safe', 'scam', or NULL (pending)
    user2_answer VARCHAR(10),
    -- 'safe', 'scam', or NULL (pending)
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'completed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Index for faster lookups by message_id
CREATE INDEX IF NOT EXISTS idx_cyber_challenges_message_id ON cyber_challenges(message_id);