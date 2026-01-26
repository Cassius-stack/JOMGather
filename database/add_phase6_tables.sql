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


