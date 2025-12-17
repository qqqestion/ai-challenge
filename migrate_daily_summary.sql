-- Migration script for adding Daily Summary feature
-- Run this if you already have an existing database

-- Add new columns to user_settings table
-- SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we use a workaround

-- Check if columns exist by attempting to add them
-- If they already exist, the ALTER TABLE will fail, which is fine

-- Add github_username column
ALTER TABLE user_settings ADD COLUMN github_username VARCHAR(100);

-- Add daily_summary_enabled column
ALTER TABLE user_settings ADD COLUMN daily_summary_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Add daily_summary_time column (06:00 UTC = 09:00 MSK)
ALTER TABLE user_settings ADD COLUMN daily_summary_time TIME NOT NULL DEFAULT '06:00:00';

-- Add timezone column
ALTER TABLE user_settings ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow';

-- Update schema version
INSERT INTO schema_versions (version, description) 
VALUES (2, 'Added daily GitHub summary feature: github_username, daily_summary_enabled, daily_summary_time, timezone');

