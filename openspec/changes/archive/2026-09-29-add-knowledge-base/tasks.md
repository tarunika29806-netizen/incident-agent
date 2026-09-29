# Tasks

## 1. Project Dependencies & Database Migration

- [x] 1.1 Create `requirements.txt` with project dependencies (`google-genai`, `langchain-google-genai`, `psycopg`, `psycopg-pool`, `pgvector`, `python-dotenv`, `pytest`, `pytest-mock`) and verify installation in the virtual environment.
- [x] 1.2 Create `db/migrations/001_incident_docs.sql` containing `pgvector` extension creation, `incident_docs` table schema with vector(768) column, and `match_incident_docs` RPC cosine similarity search function. Verify SQL file syntax and structural completeness.

## 2. Seed Script & Unit Tests

- [x] 2.1 Create `seed_rag.py` to embed and seed the three runbooks (Auth 504 timeouts, Database high latency, Payment gateway failures) using Gemini embeddings with idempotent upsert/existence checks. Verify the script runs and handles missing API keys or DB connections gracefully.
- [x] 2.2 Create unit/integration tests in `tests/test_seed_rag.py` using `pytest` and `pytest-mock` to test `seed_rag.py` and runbook search with fully mocked Gemini API and database connection. Verify tests pass using `pytest`.
