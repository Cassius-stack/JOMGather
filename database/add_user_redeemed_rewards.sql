-- User Redeemed Rewards Table
-- Tracks rewards that users have redeemed from the store
CREATE TABLE IF NOT EXISTS user_redeemed_rewards (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    reward_id INTEGER NOT NULL,
    reward_name VARCHAR(100) NOT NULL,
    reward_image VARCHAR(100),
    reward_code VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'available',
    -- 'available' or 'redeemed'
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Index for faster lookups by user
CREATE INDEX IF NOT EXISTS idx_user_redeemed_rewards_user_id ON user_redeemed_rewards(user_id);