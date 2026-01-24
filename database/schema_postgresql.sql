-- JOMGather Database Schema
-- PostgreSQL (Supabase) Version
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('youth', 'senior')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
-- Slice of Life displays
CREATE TABLE IF NOT EXISTS slice_of_life (
    display_id SERIAL PRIMARY KEY,
    pair_id INTEGER NOT NULL,
    prompt_image VARCHAR(255),
    youth_story TEXT,
    senior_story TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pair_id) REFERENCES pairs(pair_id)
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

