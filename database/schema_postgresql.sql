-- JOMGather Database Schema
-- PostgreSQL (Supabase) Version
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('youth', 'senior')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Profiles table
CREATE TABLE IF NOT EXISTS profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    bio TEXT,
    profile_picture VARCHAR(255),
    peak_hours VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- Interests table
CREATE TABLE IF NOT EXISTS interests (
    interest_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);
-- User interests junction table
CREATE TABLE IF NOT EXISTS user_interests (
    user_id INTEGER NOT NULL,
    interest_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, interest_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (interest_id) REFERENCES interests(interest_id) ON DELETE CASCADE
);
-- Languages table
CREATE TABLE IF NOT EXISTS languages (
    language_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);
-- User languages junction table
CREATE TABLE IF NOT EXISTS user_languages (
    user_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, language_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (language_id) REFERENCES languages(language_id) ON DELETE CASCADE
);
-- Pairs table (for matching users)
CREATE TABLE IF NOT EXISTS pairs (
    pair_id SERIAL PRIMARY KEY,
    youth_id INTEGER NOT NULL,
    senior_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'trial', 'confirmed', 'ended')
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (youth_id) REFERENCES users(user_id),
    FOREIGN KEY (senior_id) REFERENCES users(user_id)
);
-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id)
);

-- Friendships table (generic social graph)
CREATE TABLE IF NOT EXISTS friendships (
    friendship_id SERIAL PRIMARY KEY,
    user_id_1 INTEGER NOT NULL,
    user_id_2 INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id_1) REFERENCES users(user_id),
    FOREIGN KEY (user_id_2) REFERENCES users(user_id)
);
-- Slice of Life prompts (daily questions)
CREATE TABLE IF NOT EXISTS sol_prompts (
    prompt_id SERIAL PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    active_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Slice of Life displays (the combined result)
CREATE TABLE IF NOT EXISTS sol_displays (
    display_id SERIAL PRIMARY KEY,
    prompt_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    partner_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    is_public BOOLEAN DEFAULT FALSE,
    is_private BOOLEAN DEFAULT TRUE,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES sol_prompts(prompt_id),
    FOREIGN KEY (creator_id) REFERENCES users(user_id),
    FOREIGN KEY (partner_id) REFERENCES users(user_id)
);

-- Slice of Life submissions (each user's contribution)
CREATE TABLE IF NOT EXISTS sol_submissions (
    submission_id SERIAL PRIMARY KEY,
    display_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    image_url VARCHAR(255),
    thought TEXT,
    comment TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Slice of Life invites (pending invite requests)
CREATE TABLE IF NOT EXISTS sol_invites (
    invite_id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    display_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (recipient_id) REFERENCES users(user_id),
    FOREIGN KEY (prompt_id) REFERENCES sol_prompts(prompt_id),
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id)
);
-- Communities table
CREATE TABLE IF NOT EXISTS communities (
    community_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);
-- Community members junction table
CREATE TABLE IF NOT EXISTS community_members (
    community_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (community_id, user_id),
    FOREIGN KEY (community_id) REFERENCES communities(community_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    skill_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT
);
-- User skills junction table
CREATE TABLE IF NOT EXISTS user_skills (
    user_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    skill_type VARCHAR(10) CHECK (skill_type IN ('offering', 'seeking')),
    proficiency VARCHAR(20),
    PRIMARY KEY (user_id, skill_id, skill_type),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);
-- Support requests table
CREATE TABLE IF NOT EXISTS support_requests (
    request_id SERIAL PRIMARY KEY,
    elder_id INTEGER NOT NULL,
    student_id INTEGER,
    request_type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    estimated_duration INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (elder_id) REFERENCES users(user_id),
    FOREIGN KEY (student_id) REFERENCES users(user_id)
);
-- Coins table
CREATE TABLE IF NOT EXISTS coins (
    user_id INTEGER PRIMARY KEY,
    total_coins INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- Badges table
CREATE TABLE IF NOT EXISTS badges (
    badge_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(255),
    requirement TEXT
);
-- User badges junction table
CREATE TABLE IF NOT EXISTS user_badges (
    user_id INTEGER NOT NULL,
    badge_id INTEGER NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, badge_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE
);


-- Insert default interests (PostgreSQL syntax)
INSERT INTO interests (name)
VALUES ('cooking'),
    ('gardening'),
    ('music'),
    ('technology'),
    ('crafts'),
    ('reading'),
    ('exercise'),
    ('games'),
    ('travel') ON CONFLICT (name) DO NOTHING;
-- Insert default languages
INSERT INTO languages (name)
VALUES ('english'),
    ('mandarin'),
    ('malay'),
    ('tamil') ON CONFLICT (name) DO NOTHING;



-- ASK a Grandfriend

   author_name TEXT NOT NULL DEFAULT 'Anonymous',
   author_type TEXT NOT NULL CHECK (author_type IN ('grandparent', 'student')) DEFAULT 'grandparent',
   is_anonymous BOOLEAN DEFAULT FALSE,
   likes_count INTEGER DEFAULT 0,
   replies_count INTEGER DEFAULT 0,
   created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
   updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Replies Table
CREATE TABLE IF NOT EXISTS replies (
   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
   question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
   content TEXT NOT NULL,
   author_id UUID,
   author_name TEXT NOT NULL DEFAULT 'Anonymous',
   author_type TEXT NOT NULL CHECK (author_type IN ('grandparent', 'student')) DEFAULT 'student',
   is_helpful BOOLEAN DEFAULT FALSE,
   likes_count INTEGER DEFAULT 0,
   created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Question Likes Table (to track who liked what)
CREATE TABLE IF NOT EXISTS question_likes (
   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
   question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
   user_id UUID NOT NULL,
   created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
   UNIQUE(question_id, user_id)
);
-- Reply Likes Table
CREATE TABLE IF NOT EXISTS reply_likes (
   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
   reply_id UUID NOT NULL REFERENCES replies(id) ON DELETE CASCADE,
   user_id UUID NOT NULL,
   created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
   UNIQUE(reply_id, user_id)
);
-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_author_type ON questions(author_type);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_replies_question_id ON replies(question_id);
-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE replies ENABLE ROW LEVEL SECURITY;
-- Allow public read access
CREATE POLICY "Public read access" ON questions FOR SELECT USING (true);
CREATE POLICY "Public read access" ON replies FOR SELECT USING (true);
-- Allow authenticated insert
CREATE POLICY "Authenticated insert" ON questions FOR INSERT WITH CHECK (true);
CREATE POLICY "Authenticated insert" ON replies FOR INSERT WITH CHECK (true);
-- =====================================================
-- Ask A Grandfriend Database Schema
-- Run these SQL statements in your Supabase SQL Editor
-- =====================================================
-- Questions Table
CREATE TABLE IF NOT EXISTS questions (
   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
   title TEXT NOT NULL,
   content TEXT,
   category TEXT NOT NULL CHECK (category IN ('tech', 'cooking', 'cultural', 'modern', 'mentoring')),
   author_id UUID,

database/reset_replies_table.sql


-- FIX: Enable Public Access to Questions
-- Run this if users cannot see questions posted by others

-- 1. Enable RLS (Safety first)
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- 2. Allow EVERYONE to READ questions (Public Read)
-- This fixes the issue where one user cannot see another's posts
DROP POLICY IF EXISTS "Public Read Access" ON questions;
CREATE POLICY "Public Read Access" ON questions FOR SELECT USING (true);

-- 3. Allow EVERYONE to INSERT (Protected by App Logic)
DROP POLICY IF EXISTS "Public Insert Access" ON questions;
CREATE POLICY "Public Insert Access" ON questions FOR INSERT WITH CHECK (true);

-- 4. Allow EVERYONE to DELETE (Protected by App Logic)
-- Note: Our Python backend verifies ownership before deleting.
DROP POLICY IF EXISTS "Public Delete Access" ON questions;
CREATE POLICY "Public Delete Access" ON questions FOR DELETE USING (true);

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


-- Create replies table for AskAGrandfriend
CREATE TABLE IF NOT EXISTS replies (
    reply_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(user_id),
    content TEXT NOT NULL,
    author_name VARCHAR(100),
    author_type VARCHAR(50), -- 'student' or 'grandparent'
    is_approved BOOLEAN DEFAULT FALSE, -- For 'Grandfriend Approved Best Answer'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE replies ENABLE ROW LEVEL SECURITY;

-- Public Access Policies (Matching questions table for prototype)
CREATE POLICY "Public Read Replies" ON replies FOR SELECT USING (true);
CREATE POLICY "Public Insert Replies" ON replies FOR INSERT WITH CHECK (true);
CREATE POLICY "Public Delete Replies" ON replies FOR DELETE USING (true);


-- Add user_id to questions table to track ownership
-- Run this in your Supabase SQL Editor if the column doesn't exist

-- If table doesn't exist (basic structure)
CREATE TABLE IF NOT EXISTS questions (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    category VARCHAR(50),
    author_name VARCHAR(100),
    author_type VARCHAR(50),
    is_anonymous BOOLEAN DEFAULT FALSE,
    user_id INTEGER REFERENCES users(user_id), -- Link to users table
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- If table exists but missing user_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'questions' AND column_name = 'user_id') THEN
        ALTER TABLE questions ADD COLUMN user_id INTEGER REFERENCES users(user_id);
    END IF;
END $$;


-- Migration: Add profile columns to users table
-- Run this in Supabase SQL Editor when ready to persist profile data

-- Add age column
ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER;

-- Add region column
ALTER TABLE users ADD COLUMN IF NOT EXISTS region VARCHAR(50);

-- Add hobbies column (array of text)
ALTER TABLE users ADD COLUMN IF NOT EXISTS hobbies TEXT[];

-- Add skills column (array of text)
ALTER TABLE users ADD COLUMN IF NOT EXISTS skills TEXT[];

-- Verify the columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type VARCHAR(20) CHECK (type IN ('friend_request', 'sol_invite', 'sol_accept', 'sol_complete', 'sol_comment', 'sol_like')),
    message TEXT NOT NULL,
    link VARCHAR(255),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Slice of Life Prompts
CREATE TABLE IF NOT EXISTS sol_prompts (
    prompt_id SERIAL PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    active_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Slice of Life Displays (The conversation container)
CREATE TABLE IF NOT EXISTS sol_displays (
    display_id SERIAL PRIMARY KEY,
    prompt_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    partner_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    is_public BOOLEAN DEFAULT FALSE,
    is_private BOOLEAN DEFAULT TRUE,
    title VARCHAR(255),
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES sol_prompts(prompt_id),
    FOREIGN KEY (creator_id) REFERENCES users(user_id),
    FOREIGN KEY (partner_id) REFERENCES users(user_id)
);

-- Slice of Life Submissions (Individual entries)
CREATE TABLE IF NOT EXISTS sol_submissions (
    submission_id SERIAL PRIMARY KEY,
    display_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    image_url VARCHAR(255),
    thought TEXT,
    comment TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Slice of Life Invites
CREATE TABLE IF NOT EXISTS sol_invites (
    invite_id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    display_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (recipient_id) REFERENCES users(user_id),
    FOREIGN KEY (prompt_id) REFERENCES sol_prompts(prompt_id),
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id)
);

-- Slice of Life Comments (Public/Private)
CREATE TABLE IF NOT EXISTS sol_comments (
    comment_id SERIAL PRIMARY KEY,
    display_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Slice of Life Likes
CREATE TABLE IF NOT EXISTS sol_likes (
    user_id INTEGER NOT NULL,
    display_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, display_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (display_id) REFERENCES sol_displays(display_id) ON DELETE CASCADE
);

-- Create table for storing Boomerang meetup history
CREATE TABLE IF NOT EXISTS meetup_history (
    history_id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    met_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER DEFAULT 0,
    FOREIGN KEY (user1_id) REFERENCES users(user_id),
    FOREIGN KEY (user2_id) REFERENCES users(user_id)
);

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

-- Community Channels and Messages Schema
-- Run this in Supabase SQL Editor

-- Community Channels table
CREATE TABLE IF NOT EXISTS community_channels (
    channel_id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(community_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    is_announcement BOOLEAN DEFAULT FALSE,
    created_by INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Community Channel Messages table
CREATE TABLE IF NOT EXISTS community_messages (
    message_id SERIAL PRIMARY KEY,
    channel_id INTEGER NOT NULL REFERENCES community_channels(channel_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    content TEXT NOT NULL,
    reply_to_id INTEGER REFERENCES community_messages(message_id),
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Message Reactions table
CREATE TABLE IF NOT EXISTS community_message_reactions (
    reaction_id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES community_messages(message_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, user_id, emoji)
);

-- Community Roles table (admins, moderators)
CREATE TABLE IF NOT EXISTS community_roles (
    role_id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(community_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'moderator')),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(community_id, user_id, role)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_community_channels_community ON community_channels(community_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_channel ON community_messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_created ON community_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_roles_community ON community_roles(community_id);

-- Run this in your Supabase SQL Editor
-- This adds the link between Supabase Auth (UUID) and your Application Users (Integer ID)

ALTER TABLE users 
ADD COLUMN auth_id UUID UNIQUE;

-- Optional: Create an index for faster lookups
CREATE INDEX idx_users_auth_id ON users(auth_id);
