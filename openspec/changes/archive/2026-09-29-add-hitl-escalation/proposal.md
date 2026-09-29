# Proposal

## Why

The triage agent can detect degraded services and identify the need for manual intervention,
but currently has no mechanism to act on that signal � it can only set a flag in state.
We need a real escalation tool that pages the on-call team, but escalation must never happen
autonomously: every invocation must pause the agent and wait for an engineer to approve or
reject it before any ticket is created.

## What Changes

- Add `escalate_ticket(ticket_title, severity)` tool � marked **CRITICAL** (sensitive, requires human approval before execution).
- Add a `sensitive_tools` node in the LangGraph graph that holds only `escalate_ticket`.
- Add a `route_tools` router that dispatches tool calls to `safe_tools` (read-only) or `sensitive_tools` (escalation).
- Compile the graph with `interrupt_before=["sensitive_tools"]` so LangGraph pauses before the sensitive node executes.
- On **approval**: caller resumes by invoking the graph with `None` input; `escalate_ticket` then executes normally.
- On **rejection**: caller calls `graph.update_state(as_node="sensitive_tools")` to inject a `ToolMessage` of `"Rejected by engineer: <reason>"` into state, then resumes with `None` input; the agent receives the rejection and stops escalation.
- Update the system prompt to instruct the agent to escalate when manual intervention is needed **or** the service remains degraded after runbook review.
- Update tests to cover the pause/resume/reject paths using mocked LLM tool calls and `MemorySaver`.
- The route_tools router must inspect every tool call in the message. If any
  tool call is sensitive, the entire message must be routed through
  sensitive_tools so that no sensitive action can execute without approval.
- Approval must identify all pending sensitive tool calls.
- Rejection must provide a ToolMessage response for every pending sensitive
  tool call.

## Capabilities

### New Capabilities

- `hitl-approval`: Human-in-the-loop approval gate � pauses graph execution before a sensitive tool node runs, supports approve and reject resume paths, and ensures no escalation action executes without explicit engineer sign-off.

### Modified Capabilities

- `triage-agent`: Add escalation tool invocation requirement; update system prompt rule to escalate when service stays degraded. The existing health-check and runbook-search requirements are unchanged.

## Impact

- **`agent.py`**: New `escalate_ticket` tool, `sensitive_tools` node, `route_tools` router, updated graph compile call with `interrupt_before`, updated system prompt, updated `get_agent_app()`.
- **`tests/test_agent.py`**: New test cases for pause, approve, and reject paths.
- **`requirements.txt`**: No new packages required; `langgraph` and `langgraph-checkpoint-postgres` already present.
- **No breaking changes** to existing safe-tool loop or checkpointer integration.

**Rollback**: Revert `agent.py` to remove the `escalate_ticket` tool, `sensitive_tools` node, `route_tools` router, and `interrupt_before` from the compile call; restore the previous system prompt. The `safe_tools` loop and `PostgresSaver` checkpointer are unaffected. No migration or schema change is required.

**Capability affected**: `triage-agent` (modified), `hitl-approval` (new).
