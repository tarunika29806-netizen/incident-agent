# Spec Delta: knowledge-base

## Purpose

Provides a pgvector-backed incident runbook store with Gemini embedding generation and cosine similarity search for incident triage investigation.

## ADDED Requirements

### Requirement: Database Schema and Extension
The database migration script `001_incident_docs.sql` SHALL enable the `vector` extension and create the `incident_docs` table with `id`, `content`, `metadata` (jsonb), and `embedding` (vector(768)). It SHALL also create a `match_incident_docs` RPC function that computes cosine similarity search over `incident_docs`.

#### Scenario: Migration Script Execution
- **GIVEN** a clean PostgreSQL database with vector extension support
- **WHEN** `001_incident_docs.sql` is executed
- **THEN** the `incident_docs` table and `match_incident_docs` function MUST be created without errors

### Requirement: Idempotent Runbook Seeding
The seeding script `seed_rag.py` SHALL load runbook entries for auth 504 timeouts, database high latency, and payment gateway failures into `incident_docs`. Seeding MUST be idempotent: re-running `seed_rag.py` multiple times MUST update or skip existing entries without creating duplicate runbooks.

#### Scenario: First-time Seeding
- **GIVEN** an empty `incident_docs` table and a mock embedding provider returning 768-dimensional vectors
- **WHEN** `seed_rag.py` is executed
- **THEN** three distinct runbooks MUST be present in `incident_docs` with 768-dimensional embeddings

#### Scenario: Idempotent Re-seeding
- **GIVEN** `incident_docs` already contains the three seeded runbooks
- **WHEN** `seed_rag.py` is executed a second time
- **THEN** the total count of runbooks in `incident_docs` MUST remain exactly three

### Requirement: Similarity Match Function
The `match_incident_docs` SQL RPC function SHALL accept a query embedding vector, match threshold float, and match count integer, returning matching content, metadata, and similarity score sorted by similarity descending.

#### Scenario: Query Matching Runbook
- **GIVEN** seeded runbooks in `incident_docs` and a query embedding vector matching the auth service runbook
- **WHEN** `match_incident_docs` is invoked with match threshold 0.5 and match count 2
- **THEN** the function MUST return the auth service runbook as the top result with a similarity score greater than or equal to 0.5
