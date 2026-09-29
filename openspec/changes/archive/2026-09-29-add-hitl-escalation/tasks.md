# Tasks

## 1. Escalation Tool and Routing

- [x] 1.1 Add `escalate_ticket(ticket_title, severity)` tool to `agent.py` — returns a JSON string with a mock ticket ID and confirm it appears in `SENSITIVE_TOOLS` but NOT in `SAFE_TOOLS`
- [x] 1.2 Add `SENSITIVE_TOOLS = [escalate_ticket]` list alongside existing `SAFE_TOOLS` in `agent.py`
- [ ] 1.3 Replace the `route_next` function with a `route_tools` router that reads tool call names from the last AI message and returns `"safe_tools"`, `"sensitive_tools"`, or `END` accordingly; verify via a unit test that a mocked message with `escalate_ticket` routes to `"sensitive_tools"` and a mocked message with `query_service_health` routes to `"safe_tools"`
- [ ] 1.4 Add a unit test for the mixed-call routing rule: given an AI message containing both a safe tool call (`query_service_health`) and a sensitive one (`escalate_ticket`), assert that `route_tools` returns `"sensitive_tools"` (not `"safe_tools"`); run with `python -m pytest tests/test_agent.py::test_route_tools_mixed -v`

## 2. Graph Restructure with HITL Interrupt

- [x] 2.1 Add a `sensitive_tools` node (`ToolNode(SENSITIVE_TOOLS)`) to the graph in `get_agent_app()` and wire `route_tools` as the conditional edge out of `agent`, with edges from both tool nodes back to `agent`
- [x] 2.2 Update `workflow.compile(...)` to pass `interrupt_before=["sensitive_tools"]` alongside the checkpointer; verify via `python -c "from agent import get_agent_app; g = get_agent_app(); print(g.interrupt_before_nodes)"` that `sensitive_tools` appears in the interrupt list

## 3. System Prompt Update

- [x] 3.1 Update `SYSTEM_PROMPT` in `agent.py` to instruct the LLM to call `escalate_ticket` when manual intervention is needed or the service remains degraded after runbook review; verify the string contains the escalation instruction by running `python -c "from agent import SYSTEM_PROMPT; assert 'escalat' in SYSTEM_PROMPT.lower()"`

## 4. Tests — Pause, Approve, and Reject Paths

- [ ] 4.1 Add `test_hitl_pause` to `tests/test_agent.py`: mock the LLM to emit an `escalate_ticket` tool call, invoke the graph, assert execution paused before `sensitive_tools` (the pending interrupt is surfaced in graph state or the last message contains the tool call and the tool was not called), and confirm `escalate_ticket` was not executed; run with `python -m pytest tests/test_agent.py::test_hitl_pause -v`
- [ ] 4.2 Add `test_hitl_approve` to `tests/test_agent.py`: starting from the paused state of 4.1, resume with `None` input, assert `escalate_ticket` was called and the graph ran to completion; run with `python -m pytest tests/test_agent.py::test_hitl_approve -v`
- [ ] 4.3 Add `test_hitl_reject` to `tests/test_agent.py`: starting from the paused state of 4.1, inject a `ToolMessage("Rejected by engineer: not approved", tool_call_id=...)` via `graph.update_state(as_node="sensitive_tools")`, resume with `None`, assert `escalate_ticket` was NOT called and the rejection message appears in final state; run with `python -m pytest tests/test_agent.py::test_hitl_reject -v`
- [ ] 4.4 Run the full test suite and confirm all existing and new tests pass: `python -m pytest -q`
