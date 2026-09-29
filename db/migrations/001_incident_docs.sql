-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create incident_docs table
CREATE TABLE IF NOT EXISTS incident_docs (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding VECTOR(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique index on metadata title to support idempotent seeding
CREATE UNIQUE INDEX IF NOT EXISTS idx_incident_docs_title 
ON incident_docs ((metadata->>'title'));

-- Create match_incident_docs RPC cosine similarity search function
CREATE OR REPLACE FUNCTION match_incident_docs (
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.0,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    incident_docs.id,
    incident_docs.content,
    incident_docs.metadata,
    (1 - (incident_docs.embedding <=> query_embedding))::FLOAT AS similarity
  FROM incident_docs
  WHERE incident_docs.embedding IS NOT NULL
    AND (1 - (incident_docs.embedding <=> query_embedding)) >= match_threshold
  ORDER BY incident_docs.embedding <=> query_embedding ASC
  LIMIT match_count;
END;
$$;
