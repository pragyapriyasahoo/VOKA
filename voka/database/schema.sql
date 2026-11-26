-- Voka Database Schema with Migrations
-- Version 1: Initial schema
-- Version 2: Add dedup index, updated_at trigger, fix emotion confidence
-- Version 3: Add documents table for knowledge base

-- Migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Core tables (idempotent - IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    character_id UUID NOT NULL REFERENCES characters(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    language TEXT,
    emotion TEXT,
    emotion_confidence REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    character_id UUID NOT NULL REFERENCES characters(id),
    memory_type TEXT NOT NULL CHECK (memory_type IN ('preference', 'fact', 'emotion_context')),
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 1.0,
    source_message_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emotion_events (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES messages(id),
    emotion TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_character_id ON memories(character_id);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at);
CREATE INDEX IF NOT EXISTS idx_emotion_events_message_id ON emotion_events(message_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Migration 2: Deduplication index for memories
-- Prevents duplicate memory entries for the same user/character/content
CREATE UNIQUE INDEX IF NOT EXISTS uq_memories_user_character_content 
    ON memories (user_id, character_id, content);

-- Migration 2: Updated_at trigger for memories
CREATE OR REPLACE FUNCTION update_memories_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_update_memories_updated_at ON memories;
CREATE TRIGGER trigger_update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_memories_updated_at();

-- Migration 2: Updated_at trigger for users
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_update_users_updated_at ON users;
CREATE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_updated_at();

-- Record migration version 1
INSERT INTO schema_migrations (version, description) 
VALUES (1, 'Initial schema')
ON CONFLICT (version) DO NOTHING;

-- Record migration version 2
INSERT INTO schema_migrations (version, description) 
VALUES (2, 'Add dedup index, updated_at triggers, fix emotion confidence NOT NULL')
ON CONFLICT (version) DO NOTHING;

-- Migration 3: Documents table for knowledge base tracking
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    language TEXT NOT NULL DEFAULT 'english',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);

-- Updated_at trigger for documents
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_update_documents_updated_at ON documents;
CREATE TRIGGER trigger_update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();

-- Record migration version 3
INSERT INTO schema_migrations (version, description) 
VALUES (3, 'Add documents table for knowledge base tracking')
ON CONFLICT (version) DO NOTHING;