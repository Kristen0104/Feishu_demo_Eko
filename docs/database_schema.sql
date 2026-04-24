-- Eko 数据库结构文档
-- PostgreSQL + pgvector

-- =============================================
-- 1. 用户表 (users)
-- =============================================
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    feishu_open_id VARCHAR(128) UNIQUE,
    name VARCHAR(256) NOT NULL,
    avatar_url VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 2. 会话表 (sessions)
-- =============================================
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(256),
    is_pinned BOOLEAN DEFAULT FALSE,
    last_intent VARCHAR(32),  -- CHAT/DOC/PPT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- =============================================
-- 3. 任务表 (tasks)
-- =============================================
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    result TEXT,
    intent VARCHAR(32) NOT NULL,  -- CHAT/DOC/PPT
    status VARCHAR(32) DEFAULT 'pending',  -- pending/running/completed/failed
    plan_steps JSONB,  -- JSON array of task steps
    result_url VARCHAR(512),
    bitable_id VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_session_id ON tasks(session_id);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);

-- =============================================
-- 4. 画布元素表 (canvas_elements)
-- =============================================
CREATE TABLE canvas_elements (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    element_type VARCHAR(64) NOT NULL,  -- shape/text/arrow/card
    data JSONB NOT NULL,  -- Tldraw element JSON
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_canvas_session_id ON canvas_elements(session_id);

-- =============================================
-- 5. 画布快照表 (canvas_snapshots)
-- =============================================
CREATE TABLE canvas_snapshots (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    snapshot JSONB NOT NULL,  -- Full Tldraw JSON
    version INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snapshots_session_id ON canvas_snapshots(session_id);

-- =============================================
-- 6. RAG 文件表 (rag_files)
-- =============================================
CREATE TABLE rag_files (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE SET NULL,
    filename VARCHAR(256) NOT NULL,
    file_type VARCHAR(32) NOT NULL,  -- pdf/docx/txt
    file_path VARCHAR(512) NOT NULL,  -- Storage path
    status VARCHAR(32) DEFAULT 'pending',  -- pending/processing/completed/failed
    vector_ids VARCHAR[],
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rag_files_user_id ON rag_files(user_id);
CREATE INDEX idx_rag_files_session_id ON rag_files(session_id);

-- =============================================
-- 7. 飞书 Bitable 配置表 (feishu_bitable_config)
-- =============================================
CREATE TABLE feishu_bitable_config (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    app_token VARCHAR(128) NOT NULL,
    table_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 8. pgvector 向量表 (for RAG)
-- =============================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_vectors (
    id BIGSERIAL PRIMARY KEY,
    file_id VARCHAR(36) NOT NULL REFERENCES rag_files(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rag_vectors_file_id ON rag_vectors(file_id);
CREATE INDEX idx_rag_vectors_embedding ON rag_vectors USING ivfflat (embedding vector_cosine_ops);

-- =============================================
-- 触发器: 自动更新 updated_at
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_canvas_elements_updated_at BEFORE UPDATE ON canvas_elements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rag_files_updated_at BEFORE UPDATE ON rag_files FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_feishu_bitable_config_updated_at BEFORE UPDATE ON feishu_bitable_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
