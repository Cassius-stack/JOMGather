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
