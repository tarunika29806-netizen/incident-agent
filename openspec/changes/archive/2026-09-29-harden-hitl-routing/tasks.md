# Tasks

## 1. Harden HITL routing

- [x] 1.1 Update `route_tools` in `agent.py` to inspect every tool call in the latest AI message and route to `sensitive_tools` when any sensitive tool is present; verify with a mixed safe-and-sensitive routing test.
- [x] 1.2 Preserve the existing `interrupt_before=["sensitive_tools"]` graph configuration and verify that a sensitive tool call pauses before execution.
- [x] 1.3 Add pytest coverage using mocked LLM/tool behavior to verify that a model response containing both `query_service_health` and `escalate_ticket` requires HITL approval and does not execute the sensitive action before approval.

## 2. Handle multiple pending approvals

- [x] 2.1 Update the service-layer pending approval handling to collect every pending sensitive tool call for a thread; verify that multiple `escalate_ticket` calls are returned as pending approvals.
- [x] 2.2 Update the approval path to resume the same thread and allow every pending sensitive action to execute after approval; verify the returned approval state contains all approved actions.
- [x] 2.3 Update the rejection path to create one `ToolMessage` containing `Rejected by engineer: <reason>` for every pending sensitive tool call; verify each message uses the corresponding tool-call ID and no sensitive tool executes.
- [x] 2.4 Add pytest coverage with mocked LLM/tool behavior and mocked database/checkpointer state for rejecting multiple pending sensitive calls; verify all pending calls receive rejection messages and the sensitive tools are not executed.

## 3. Integration and specification validation

- [x] 3.1 Validate the completed OpenSpec change with `openspec validate harden-hitl-routing` and verify validation succeeds.
- [x] 3.2 Run `python -m pytest -q` and verify the complete test suite passes, including the mixed safe-and-sensitive and multiple-rejection regression tests.
- [x] 3.3 Verify the change artifacts `proposal.md`, `specs/hitl-approval/spec.md`, `design.md`, and `tasks.md` are present and consistent with the implemented HITL routing behavior.

