# Proposal: Add Triage Agent Core

## Why

When an engineer describes an incident in plain English, an AI agent needs to autonomously investigate service health, retrieve relevant runbooks from the knowledge base, and synthesize an incident diagnosis and recommended remediation. This core agent logic is required before adding human-in-the-loop approval and user interfaces.

## What Changes

- Add `langgraph` dependency to `requirements.txt`.
- Create `agent.py` defining the core LangGraph state machine (`AgentState` schema and graph flow).
- Implement mock backend health check tools for inspectable services (`auth`, `database`, `payments`).
- Implement runbook retrieval tool querying the `incident_docs` pgvector table via `match_incident_docs`.
- Implement Gemini LLM reasoning node (`langchain-google-genai`) to produce incident summaries and set `requires_escalation` flags.
- Add unit/integration tests in `tests/test_agent.py` mocking Gemini LLM calls and health check tools.

## Capabilities

### New Capabilities
- `triage-agent`: Autonomous incident investigation using LangGraph, service health diagnostics, runbook retrieval, and LLM reasoning.

### Modified Capabilities
- None.

## Impact

- **Agent Engine**: Introduces `agent.py` with LangGraph graph definition.
- **Dependencies**: Adds `langgraph` to `requirements.txt`.
- **Testing**: Adds `tests/test_agent.py`.

## Rollback

To roll back this change:
1. Remove `agent.py` and `tests/test_agent.py`.
2. Remove `langgraph` from `requirements.txt`.
