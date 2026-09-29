\# Design



\## Context



The agent uses LangGraph to route model-generated tool calls into safe and

sensitive tool nodes. The existing graph already pauses before

`sensitive\_tools`, and `escalate\_ticket` is classified as a sensitive action.



The change affects the routing decision and the service-layer handling of

pending approvals. The implementation must preserve the existing LangGraph

interrupt and PostgresSaver checkpointing behavior.



See `proposal.md` for the motivation and scope.



\## Goals / Non-Goals



\*\*Goals:\*\*



\- Inspect every tool call in a model response before selecting the tool node.

\- Route the entire response to `sensitive\_tools` when at least one sensitive

&#x20; tool call is present.

\- Preserve the existing interrupt boundary before sensitive tool execution.

\- Represent all pending sensitive calls when approval is requested.

\- Handle rejection for every pending sensitive call by creating a corresponding

&#x20; `ToolMessage`.

\- Keep the existing thread-based checkpointing and approval/resume flow.

\- Add regression coverage for mixed safe and sensitive tool calls.

\- Avoid introducing new dependencies or changing the existing API structure.



\*\*Non-Goals:\*\*



\- Changing which tools are classified as safe or sensitive.

\- Changing the behavior of `escalate\_ticket` itself.

\- Replacing LangGraph's interrupt mechanism.

\- Changing the PostgresSaver persistence architecture.

\- Adding new external services or dependencies.



\## Decisions



\### 1. Inspect all tool calls before routing



The routing logic will collect the names of all tool calls in the latest

AI message and check whether the set contains any sensitive tool.



\*\*Decision:\*\* Route to `sensitive\_tools` if any sensitive tool is present.



\*\*Rationale:\*\* A model response can contain multiple tool calls. Checking only

the first call can allow a later sensitive call to bypass the approval gate.



\*\*Alternative considered:\*\* Route based only on the first tool call. This is

simpler but does not provide the required safety guarantee for mixed tool

responses.



\### 2. Treat a mixed safe and sensitive response as sensitive



When a response contains both safe and sensitive calls, the entire response

will follow the sensitive approval path.



\*\*Decision:\*\* Do not execute the safe call separately before approval.



\*\*Rationale:\*\* Keeping the complete model response behind the same approval

boundary prevents partial execution and keeps the approval decision associated

with the complete set of actions.



\*\*Alternative considered:\*\* Execute safe calls immediately and pause only for

the sensitive calls. This would require splitting one model response across

different execution paths and could produce partial side effects.



\### 3. Track every pending sensitive call



The service layer will identify all pending sensitive calls rather than only

the first matching call.



\*\*Decision:\*\* Use a collection of pending sensitive tool calls for approval

and rejection handling.



\*\*Rationale:\*\* Multiple sensitive calls can be emitted in one model response,

and every call must be accounted for before the workflow continues.



\*\*Alternative considered:\*\* Keep a single pending approval. This would leave

additional sensitive calls unresolved.



\### 4. Reject every pending sensitive call



On rejection, the service layer will create one `ToolMessage` for each pending

sensitive call using the engineer's rejection reason.



\*\*Decision:\*\* Inject all rejection messages through the existing

`sensitive\_tools` state update before resuming the graph.



\*\*Rationale:\*\* Each tool call has its own tool-call ID and must receive a

corresponding result so the model can process the rejection correctly.



\*\*Alternative considered:\*\* Reject only the first pending call. This could

leave other tool calls without a result and would not fully resolve the

model response.



\### 5. Preserve the existing interrupt and checkpoint architecture



The existing `interrupt\_before=\["sensitive\_tools"]` configuration and

PostgresSaver thread checkpointing will remain unchanged.



\*\*Decision:\*\* Harden the routing and service-layer logic without introducing

a new approval mechanism.



\*\*Rationale:\*\* The existing architecture already provides the required pause,

resume, rejection, and persistence behavior. Changing it would increase

complexity without being necessary for this change.



\*\*Alternative considered:\*\* Implement a separate application-level approval

queue. This would duplicate functionality already provided by LangGraph and

would require additional state management.



\### 6. Keep the change dependency-free



No new Python packages or external services will be introduced.



\*\*Decision:\*\* Implement the change using the existing LangGraph, FastAPI,

and PostgresSaver components.



\*\*Rationale:\*\* The project is designed for a zero-cost stack and already has

the required components.



\## Risks / Trade-offs



\- \[Risk] A mixed safe and sensitive response waits for approval before any

&#x20; tool call executes → Mitigation: Treating the complete response as sensitive

&#x20; prevents partial execution and provides one consistent approval boundary.



\- \[Risk] Multiple pending tool calls increase the amount of approval state

&#x20; that must be tracked → Mitigation: Store and process the pending sensitive

&#x20; calls as a collection and create one result message per call.



\- \[Risk] Free-tier database pooler limits or transient connections can affect

&#x20; persisted HITL state → Mitigation: Reuse the existing PostgresSaver

&#x20; connection architecture and avoid adding additional database connections.



\- \[Risk] Gemini free-tier rate limits can affect tests that invoke the real

&#x20; model → Mitigation: Regression tests for routing and HITL behavior should

&#x20; use mocked model/tool behavior rather than relying on live Gemini calls.



\- \[Risk] Render free-tier cold starts can delay a paused workflow or API

&#x20; request → Mitigation: Keep the existing thread ID and PostgresSaver

&#x20; persistence so approval state is stored outside the application process.



\- \[Risk] A rejection must match every tool call using its tool-call ID →

&#x20; Mitigation: Generate a separate `ToolMessage` for each pending sensitive

&#x20; call and preserve its original tool-call ID.



\## Migration Plan



1\. Apply the hardened routing and multi-call approval/rejection handling.

2\. Run the OpenSpec validation for `harden-hitl-routing`.

3\. Run the full Python test suite with `python -m pytest -q`.

4\. Archive the completed OpenSpec change so the updated

&#x20;  `hitl-approval` specification becomes the source of truth.

5\. Commit the code and OpenSpec artifacts together.

6\. If rollback is required, revert the Change 6 code changes and restore the

&#x20;  previous `hitl-approval` specification.



No database schema migration is required.



\## Open Questions



None.

