-- Database Schema for Chat History
-- SQLite compatible schema for persisting chat history and user state data

-- Users table: Stores user metadata
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- User settings table: Stores user LLM preferences (1:1 with users)
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini',
    temperature REAL NOT NULL DEFAULT 0.3 CHECK (temperature >= 0.0 AND temperature <= 2.0),
    summarization_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Messages table: Stores individual chat messages in conversations
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Usage stats table: Aggregated usage statistics per user (1:1 with users)
CREATE TABLE IF NOT EXISTS usage_stats (
    user_id INTEGER PRIMARY KEY,
    chat_input_tokens INTEGER NOT NULL DEFAULT 0,
    chat_output_tokens INTEGER NOT NULL DEFAULT 0,
    chat_cost REAL NOT NULL DEFAULT 0.0,
    requests_count INTEGER NOT NULL DEFAULT 0,
    summarization_count INTEGER NOT NULL DEFAULT 0,
    summarization_input_tokens INTEGER NOT NULL DEFAULT 0,
    summarization_output_tokens INTEGER NOT NULL DEFAULT 0,
    summarization_cost REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Schema versions table: Track schema changes for migration management
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_last_activity ON users(last_activity);

CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_user_created ON messages(user_id, created_at);

-- Insert initial schema version
INSERT INTO schema_versions (version, description) VALUES (1, 'Revised schema: separated user settings, 1:1 usage stats, removed current_mode');
