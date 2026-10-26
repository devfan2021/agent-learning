CREATE EXTENSION IF NOT EXISTS vector;

-- 第 2 周：文档与切片
CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(1024),
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx
    ON chunks USING gin (tsv);

-- 第 3 周：链路追踪（本地 JSONL 之外的结构化版本）
CREATE TABLE IF NOT EXISTS traces (
    id                BIGSERIAL PRIMARY KEY,
    trace_id          TEXT NOT NULL,
    run_name          TEXT NOT NULL,
    step              INT,
    event_type        TEXT NOT NULL,
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms        INT,
    prompt_tokens     INT,
    completion_tokens INT,
    cost              NUMERIC(12, 6),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS traces_trace_id_idx ON traces (trace_id);
CREATE INDEX IF NOT EXISTS traces_created_at_idx ON traces (created_at);

-- 第 4 周：评测历史，用于回归门禁
CREATE TABLE IF NOT EXISTS eval_runs (
    id             BIGSERIAL PRIMARY KEY,
    run_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    git_sha        TEXT,
    total          INT NOT NULL,
    passed         INT NOT NULL,
    pass_rate      NUMERIC(5, 4) NOT NULL,
    p95_latency_ms INT,
    avg_cost       NUMERIC(12, 6)
);
