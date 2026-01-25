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
