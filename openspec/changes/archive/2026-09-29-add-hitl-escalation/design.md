# Design

## Context

See `proposal.md` — Why for motivation.

The triage agent currently uses a single-tier graph: `agent ? safe_tools ? agent`. The
`safe_tools` node holds read-only tools (`query_service_health`, `search_remediation_runbooks`).
The agent state already tracks `requires_escalation: bool`, but escalation has no tool to
call. LangGraph's `interrupt_before` mechanism is the idiomatic way to insert a human gate
without a custom approval server.

Key constraints:
- **Supabase transaction pooler** (port 6543): `prepare_threshold=None` required on every
  `psycopg` connection to avoid prepared-statement errors.
- **Render free tier cold starts**: The `PostgresSaver` checkpointer must tolerate cold starts;
  the paused thread survives because state is persisted in Postgres, not in process memory.
- **No credit card / free tier**: No managed approval queue (e.g. AWS SQS) available; the
  approval signal is delivered by the caller (API layer or UI) directly re-invoking the graph.

## Goals / Non-Goals

**Goals:**
- Insert `escalate_ticket` as a CRITICAL tool that can only fire after engineer approval.
- Pause graph execution deterministically at the `sensitive_tools` node boundary.
- Support approve (resume with `None`) and reject (inject `ToolMessage` + resume with `None`).
- Keep all state in the existing Postgres checkpointer so paused threads survive restarts.
- Cover pause, approve, and reject paths with unit tests using `MemorySaver`.

**Non-Goals:**
- A dedicated approval UI or API endpoint (belongs in `add-triage-api` / `add-triage-ui`).
- Notification emails or PagerDuty integration (future work).
- Multi-level approval chains.
- Changing the safe-tool loop or checkpointer configuration.

## Decisions

### D1: Two-tier tool routing via `route_tools` conditional edge

**Decision**: Replace the single `route_next` edge with a `route_tools` function that reads the
last AI message's tool calls and routes to either `safe_tools` or `sensitive_tools` based on
which tool was called.

**Why**: LangGraph's `interrupt_before` fires on a named node. If all tools shared one node,
every tool call (including safe reads) would trigger the interrupt. A separate `sensitive_tools`
node lets us interrupt only on escalation.

**Alternatives considered**:
- *Single `tools` node with a guard inside*: The guard would have to run before tool execution,
  but `ToolNode` does not expose a pre-hook; we'd need a custom node anyway.
- *Separate graph for escalation*: Overly complex; breaks the single-thread state model the
  checkpointer relies on.

### D2: `interrupt_before=["sensitive_tools"]` compile option

**Decision**: Use `workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])`.

**Why**: This is LangGraph's native mechanism for HITL. It pauses the graph between the `agent`
node (which emits the tool call) and the `sensitive_tools` node (which would execute it). No
custom polling or locks are needed.

**Alternatives considered**:
- *`interrupt_after=["agent"]`*: Would also pause at the right time, but `interrupt_before`
  makes the semantics clearer: the node that would cause side effects has not started.

### D3: Rejection via `update_state(as_node="sensitive_tools")`

**Decision**: To reject, the caller injects a `ToolMessage` with content
`"Rejected by engineer: <reason>"` directly into graph state using
`graph.update_state(config, {"messages": [rejection_msg]}, as_node="sensitive_tools")`,
then resumes with `None`. The agent then reads the rejection message and terminates the
escalation path.

**Why**: This is the canonical LangGraph HITL rejection pattern. It satisfies the spec
requirement that a rejected escalation MUST NOT execute while keeping the resume path
(`None` input) uniform for both approve and reject.

**Alternatives considered**:
- *Raising an exception inside `sensitive_tools`*: Pollutes the checkpointed state and is
  not idiomatic for a user-driven rejection signal.
- *Custom `rejected: bool` state field*: Would require modifying `AgentState` and all
  existing graph nodes to check it.

### D4: `escalate_ticket` implementation — mocked for now

**Decision**: `escalate_ticket` returns a JSON string confirming ticket creation with a
mock ticket ID. Real Supabase or PagerDuty integration is deferred to a later change.

**Why**: The HITL gate is the critical behavior being specified; the tool's side effect
is testable with a deterministic mock return without external calls.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Render cold start kills paused thread | State lives in Postgres via `PostgresSaver`; resume works from any process after restart |
| `interrupt_before` on all graph invocations | Only the `sensitive_tools` node is interrupted; safe-tool loop is unaffected |
| Stale paused threads in Postgres | No TTL mechanism yet; acceptable for prototype; future work can add a cleanup job |
| `MemorySaver` tests cannot cover Postgres restart | Restart durability test is deferred to an integration test against real Supabase |
| Gemini free-tier rate limits | `escalate_ticket` is mocked and does not call Gemini; safe tools already handle rate-limit errors gracefully |

## Migration Plan

1. Update `agent.py` in place — no DB schema changes, no migration files needed.
2. Existing `safe_tools` loop is unchanged; the new `route_tools` router preserves its routing logic.
3. `get_agent_app()` adds `interrupt_before`; callers that do not need HITL can pass `interrupt_before=[]` to opt out.
4. **Rollback**: Revert `agent.py` to the previous commit — no data to migrate.

## Open Questions

None — all design decisions are resolved by the chosen LangGraph patterns.
