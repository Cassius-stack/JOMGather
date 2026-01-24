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
