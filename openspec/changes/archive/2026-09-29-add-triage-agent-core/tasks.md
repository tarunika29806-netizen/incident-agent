# Tasks

## 1. Dependency Setup & Core Agent Engine

- [x] 1.1 Add `langgraph` and `langgraph-checkpoint-postgres` to `requirements.txt` and verify installation in the virtual environment.
- [x] 1.2 Implement `agent.py` defining `psycopg_pool` `ConnectionPool` settings (`max_size 10`, `autocommit`, `connect_timeout 15`, `prepare_threshold None`), `query_service_health` tool, `search_remediation_runbooks` tool (using 768d `RETRIEVAL_QUERY` embeddings, top 2 results), `AgentState` with `add_messages`, `extract_text` normalizer, LangGraph safe tool loop (`agent` -> `safe_tools` -> `agent`), and `get_agent_app()` graph compiler with `PostgresSaver` checkpointer.

## 2. Unit & Integration Tests

- [x] 2.1 Create `tests/test_agent.py` with `pytest` and `pytest-mock` to test tool execution, `extract_text` normalization, graph routing, and thread persistence by `thread_id` with fully mocked Gemini LLM and database connections. Verify all tests pass with `python -m pytest`.
