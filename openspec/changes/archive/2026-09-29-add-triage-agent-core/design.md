# Design: Triage Agent Core

## Context

See `proposal.md` for motivation. This design covers the core LangGraph state machine (`agent.py`), safe read-only tools, and Postgres checkpointer setup for thread persistence.

## Goals / Non-Goals

**Goals:**
- Implement `AgentState` schema using `add_messages` reducer.
- Implement safe read-only tools: `query_service_health` and `search_remediation_runbooks`.
- Implement `extract_text` content normalization helper.
- Configure `psycopg_pool.ConnectionPool` and `PostgresSaver` checkpointer.
- Export `get_agent_app()` to compile the LangGraph workflow.

**Non-Goals:**
- Escalation tools or HITL approval interrupts (handled in subsequent `add-hitl-approval` change).
- REST API integration or UI mounting (handled in `add-triage-api` and `add-triage-ui`).

## Decisions

### Decision 1: Safe Tool Loop in LangGraph
- **Rationale**: The agent executes an `agent` -> `safe_tools` -> `agent` loop, terminating when the LLM returns no further tool calls (`END`). The tool registry is restricted to read-only diagnostics (`query_service_health` and `search_remediation_runbooks`).
- **Alternatives Considered**:
  - *Giving direct escalation tools to LLM*: High risk of accidental execution or prompt injection bypass.

### Decision 2: Supabase Pooler Configuration (`prepare_threshold=None`)
- **Rationale**: `psycopg_pool.ConnectionPool` is configured with `max_size=10`, `autocommit=True`, `connect_timeout=15`, and `prepare_threshold=None`. Setting `prepare_threshold=None` disables server-side prepared statements, avoiding transaction pooler (port 6543) errors on Supabase.
- **Alternatives Considered**:
  - *Direct connection without pooler*: Reaches Supabase free-tier connection limits rapidly under concurrency.

### Decision 3: Text Extraction Normalizer (`extract_text`)
- **Rationale**: Gemini models via `langchain-google-genai` can return message content as either a plain `str` or a `list[dict]` of content blocks. `extract_text` normalizes all content representations to a clean string.

## Risks / Trade-offs

- **[Risk] Supabase Pooler Disconnections during Idle Time** → **Mitigation**: `connect_timeout=15` and `autocommit=True` ensure connections reset cleanly.
- **[Risk] LLM Free Tier Quotas** → **Mitigation**: `pytest` tests use `pytest-mock` and fake LLM instances (`FakeListChatModel` or mocked invoke) so tests spend zero API tokens.
