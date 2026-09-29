# Proposal: Add Runbook Knowledge Base

## Why

To perform automated incident triage, the agent needs a vector-searchable runbook repository. We need a zero-cost database layer using Supabase Postgres with `pgvector` and Gemini embeddings (768 dimensions) to store and retrieve incident remediation runbooks for Auth, Database, and Payment services.

## What Changes

- Create `db/migrations/001_incident_docs.sql` enabling `pgvector` and creating `incident_docs` table (content, metadata, 768d embedding) and `match_incident_docs` RPC cosine similarity search function.
- Create `requirements.txt` with dependencies (`google-genai`, `langchain-google-genai`, `psycopg`, `psycopg-pool`, `pgvector`, `python-dotenv`, `pytest`, `pytest-mock`).
- Create `seed_rag.py` to seed three initial runbooks (Auth 504 timeouts, Database high latency, Payment gateway failures) idempotently using Gemini embeddings.
- Add unit/integration tests in `tests/test_seed_rag.py` mocking Gemini embeddings and Supabase database interactions.

## Capabilities

### New Capabilities
- `knowledge-base`: Storing, embedding, and retrieving incident runbooks using pgvector and Gemini embeddings.

### Modified Capabilities
- None.

## Impact

- **Database**: Adds `pgvector` extension and `incident_docs` table with `match_incident_docs` function in Supabase Postgres.
- **Dependencies**: Adds core project Python dependencies in `requirements.txt`.
- **Scripts**: Adds CLI seeder `seed_rag.py`.

## Rollback

To roll back this change:
1. Drop the `match_incident_docs` function and `incident_docs` table in Supabase via SQL migration rollback (`DROP FUNCTION IF EXISTS match_incident_docs; DROP TABLE IF EXISTS incident_docs;`).
2. Remove `seed_rag.py`, `db/migrations/001_incident_docs.sql`, and related tests.
