# Design: Knowledge Base & Vector Store

## Context

See `proposal.md` for motivation. We are establishing the runbook knowledge base using Supabase Postgres with `pgvector` and Gemini embeddings (768 dimensions).

## Goals / Non-Goals

**Goals:**
- Provide a SQL migration script `db/migrations/001_incident_docs.sql` to set up `pgvector` and `incident_docs` table.
- Implement `seed_rag.py` to embed and seed three core runbooks (Auth 504, Database high latency, Payment failures) idempotently.
- Create unit/integration tests with mocks for Gemini API and database connections.

**Non-Goals:**
- Dynamic user-uploaded runbook parsing in this change (handled in seed script for initial 3 runbooks).
- Complex chunking strategy for long documents (runbooks are concise, single-doc embedding is sufficient).

## Decisions

### Decision 1: Supabase pgvector with 768-dimensional Gemini Embeddings
- **Rationale**: `text-embedding-004` (or `models/embedding-001`) from Gemini via Google AI Studio supports `output_dimensionality=768`. Standard 768d vector storage in `pgvector` balances accuracy with low memory footprint on Supabase free tier.
- **Alternatives Considered**:
  - *ChromaDB / Pinecone*: Adds extra external services/dependencies. Supabase Postgres already provides native vector capability with `pgvector`.
  - *1536d Embeddings*: Consumes twice the memory and storage on Supabase free tier without significant gain for short runbooks.

### Decision 2: Idempotent Seeding via Service Key / Title Upsert
- **Rationale**: `seed_rag.py` computes an identifier (e.g. `service` name or `title` in JSON metadata) and performs an UPSERT or checks existence before inserting. This guarantees `seed_rag.py` can be executed safely multiple times.
- **Alternatives Considered**:
  - *Truncate and reload*: Risks dropping user data or locks if run in production.

### Decision 3: SQL Cosine Similarity RPC Function (`match_incident_docs`)
- **Rationale**: Cosine similarity (`<=>` operator in pgvector) performs well for text embeddings. Wrapping it in a SQL RPC function allows remote vector search over Supabase database connection.
- **Alternatives Considered**:
  - *L2 distance (`<->`)*: Less suited for normalized text embeddings than cosine similarity.

## Risks / Trade-offs

- **[Risk] Gemini Free Tier Rate Limits (15 RPM)** → **Mitigation**: Batch embedding requests in `seed_rag.py` with small delays if needed. Tests MUST mock embedding calls completely so no API quota is spent during `pytest`.
- **[Risk] Supabase Pooler (Port 6543) Compatibility** → **Mitigation**: Standard SQL queries in migration and seeding script use parameterized execution.
- **[Risk] Unhandled Missing Environment Variables** → **Mitigation**: `seed_rag.py` uses `python-dotenv` and validates `GEMINI_API_KEY` and `DATABASE_URL` before executing, providing clear error messages if missing.

## Migration Plan

1. Execute `db/migrations/001_incident_docs.sql` against Supabase database.
2. Run `python seed_rag.py` to seed initial runbook vectors.
3. Run `pytest tests/test_seed_rag.py` to verify functionality.
