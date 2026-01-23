-- Run this in your Supabase SQL Editor
-- This adds the link between Supabase Auth (UUID) and your Application Users (Integer ID)

ALTER TABLE users 
ADD COLUMN auth_id UUID UNIQUE;

-- Optional: Create an index for faster lookups
CREATE INDEX idx_users_auth_id ON users(auth_id);
