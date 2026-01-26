-- =====================================================
-- Supabase Row Level Security (RLS) Policies
-- =====================================================

-- 0. Helper Function to Map auth.uid() to internal user_id
CREATE OR REPLACE FUNCTION get_internal_uid() 
RETURNS INTEGER AS $$
    SELECT user_id FROM public.users WHERE auth_id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- 1. Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE sol_displays ENABLE ROW LEVEL SECURITY;
ALTER TABLE sol_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sol_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE sol_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE coins ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE communities ENABLE ROW LEVEL SECURITY;
ALTER TABLE community_members ENABLE ROW LEVEL SECURITY;

-- 2. Define Policies

-- USERS: Own data only
CREATE POLICY "Users can see their own record" ON users FOR SELECT USING (auth_id = auth.uid());
CREATE POLICY "Users can update their own record" ON users FOR UPDATE USING (auth_id = auth.uid());

-- PROFILES: Public read, own write
CREATE POLICY "Public profile view" ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can edit own profile" ON profiles FOR ALL USING (user_id = get_internal_uid());

-- MESSAGES: Involved parties only
CREATE POLICY "Message access" ON messages FOR ALL USING (
    sender_id = get_internal_uid() OR receiver_id = get_internal_uid()
);

-- FRIENDSHIPS: Involved parties only
CREATE POLICY "Friendship access" ON friendships FOR ALL USING (
    user_id_1 = get_internal_uid() OR user_id_2 = get_internal_uid()
);

-- SLICE OF LIFE: Creators/Participants or Public
CREATE POLICY "SOL Display viewing" ON sol_displays FOR SELECT USING (
    creator_id = get_internal_uid() OR partner_id = get_internal_uid() OR is_public = true
);
CREATE POLICY "SOL Display management" ON sol_displays FOR ALL USING (
    creator_id = get_internal_uid() OR partner_id = get_internal_uid()
);

CREATE POLICY "SOL Submissions viewing" ON sol_submissions FOR SELECT USING (
    user_id = get_internal_uid() OR 
    EXISTS (SELECT 1 FROM sol_displays d WHERE d.display_id = sol_submissions.display_id AND (d.creator_id = get_internal_uid() OR d.partner_id = get_internal_uid() OR d.is_public = true))
);
CREATE POLICY "SOL Submission edit" ON sol_submissions FOR ALL USING (user_id = get_internal_uid());

-- COINS: Own only
CREATE POLICY "Coin balance access" ON coins FOR SELECT USING (user_id = get_internal_uid());

-- NOTIFICATIONS: Own only
CREATE POLICY "Notification access" ON notifications FOR ALL USING (user_id = get_internal_uid());

-- GLOBAL CONTENT (Prompts, Skills, Badges): Public read
CREATE POLICY "Public Prompts read" ON sol_prompts FOR SELECT USING (true);
CREATE POLICY "Public Interests read" ON interests FOR SELECT USING (true);
CREATE POLICY "Public Languages read" ON languages FOR SELECT USING (true);
CREATE POLICY "Public Skills read" ON skills FOR SELECT USING (true);
CREATE POLICY "Public Badges read" ON badges FOR SELECT USING (true);

-- JUNCTION TABLES: Own write, public read
CREATE POLICY "Interest join/view" ON user_interests FOR ALL USING (user_id = get_internal_uid());
CREATE POLICY "Language join/view" ON user_languages FOR ALL USING (user_id = get_internal_uid());
CREATE POLICY "Skill join/view" ON user_skills FOR ALL USING (user_id = get_internal_uid());
CREATE POLICY "Badge earned access" ON user_badges FOR SELECT USING (true);

-- PAIRS: Involved parties only
CREATE POLICY "Pair access" ON pairs FOR ALL USING (
    youth_id = get_internal_uid() OR senior_id = get_internal_uid()
);

-- SUPPORT REQUESTS: Involved parties only
CREATE POLICY "Support request access" ON support_requests FOR ALL USING (
    elder_id = get_internal_uid() OR student_id = get_internal_uid()
);

-- COMMUNITIES: Public read, creator write
CREATE POLICY "Public community view" ON communities FOR SELECT USING (true);
CREATE POLICY "Community management" ON communities FOR ALL USING (created_by = get_internal_uid());
CREATE POLICY "Community member view" ON community_members FOR SELECT USING (true);
CREATE POLICY "Community joining" ON community_members FOR ALL USING (user_id = get_internal_uid());

-- INVITES (SOL): Involved parties
CREATE POLICY "SOL Invite access" ON sol_invites FOR ALL USING (
    sender_id = get_internal_uid() OR recipient_id = get_internal_uid()
);

-- ASK A GRANDFRIEND (Questions/Replies)
CREATE POLICY "Grandfriend Questions view" ON questions FOR SELECT USING (true);
CREATE POLICY "Grandfriend Questions write" ON questions FOR INSERT WITH CHECK (true);
CREATE POLICY "Grandfriend Replies view" ON replies FOR SELECT USING (true);
CREATE POLICY "Grandfriend Replies write" ON replies FOR INSERT WITH CHECK (true);

ALTER TABLE question_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE reply_likes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Like question" ON question_likes FOR ALL USING (user_id::text = auth.uid()::text);
CREATE POLICY "Like reply" ON reply_likes FOR ALL USING (user_id::text = auth.uid()::text);
