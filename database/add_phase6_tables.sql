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
