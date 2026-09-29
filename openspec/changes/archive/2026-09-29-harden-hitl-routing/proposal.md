\# Proposal



\## Why



The current HITL routing must ensure that a model response containing multiple

tool calls is paused whenever any one of those calls is sensitive. This prevents

a mixed response containing both safe and sensitive actions from bypassing the

human approval gate.



The rejection path must also handle every pending sensitive tool call so that

no sensitive action is left unresolved after an engineer rejects the request.



\## What Changes



\- Modify HITL routing so that all tool calls in an AI message are inspected.

\- If any tool call is sensitive, route the entire message through the

&#x20; `sensitive\_tools` approval gate.

\- Include every pending sensitive tool call in the approval payload.

\- Update rejection handling so every pending tool call receives a

&#x20; `ToolMessage` containing the engineer's rejection reason.

\- Add regression coverage for mixed safe and sensitive tool calls.

\- Add coverage for rejecting multiple pending sensitive calls without executing

&#x20; any sensitive action.

\- Keep the existing approval interrupt and sensitive-tool protection behavior.



\## Capabilities



\### New Capabilities



None.



\### Modified Capabilities



\- `hitl-approval`: Change the sensitive-action approval requirement so that

&#x20; any sensitive tool call in a model response causes the entire response to

&#x20; pause for approval, and rejection handles every pending sensitive call.



\## Impact



\- `agent.py`: HITL tool routing logic.

\- `service.py`: Pending approval and rejection handling.

\- `tests/test\_api.py`: Regression tests for mixed safe and sensitive calls and

&#x20; multiple pending sensitive calls.

\- `openspec/specs/hitl-approval/spec.md`: The existing HITL requirements will

&#x20; be updated after the change.

\- No new dependencies are required.

\- The existing `/chat`, `/approve`, and `/reject` API behavior remains in use.

\- Rollback: revert the Change 6 code and restore the previous

&#x20; `hitl-approval` specification if the change needs to be rolled back.

