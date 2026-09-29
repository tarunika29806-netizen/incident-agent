# Spec Delta

## Purpose

Provides a human-in-the-loop approval gate that pauses the triage agent graph before any
sensitive escalation action executes, requiring an engineer to explicitly approve or reject
each escalation before it takes effect.

## ADDED Requirements

### Requirement: Escalation tool with CRITICAL marker
The agent SHALL expose an `escalate_ticket(ticket_title, severity)` tool marked as a
CRITICAL sensitive action. This tool SHALL create an incident ticket and notify the
on-call team only after it has received engineer approval. It MUST NOT execute
autonomously without passing through the human approval gate.

#### Scenario: Tool registered as sensitive
- **GIVEN** the compiled graph with HITL support
- **WHEN** the list of sensitive tools is inspected
- **THEN** `escalate_ticket` MUST appear in `SENSITIVE_TOOLS` and NOT in `SAFE_TOOLS`

### Requirement: Graph pauses before sensitive tool execution
The LangGraph agent graph SHALL be compiled with `interrupt_before=["sensitive_tools"]`.
When the LLM emits a tool call targeting `escalate_ticket`, graph execution MUST pause
at the `sensitive_tools` node boundary and return control to the caller before the tool
executes.

#### Scenario: Pause on escalation tool call
- **GIVEN** the agent graph compiled with `interrupt_before=["sensitive_tools"]` and a mocked LLM that emits an `escalate_ticket` tool call
- **WHEN** the graph is invoked with a thread config
- **THEN** graph execution MUST pause before `sensitive_tools` runs, the last message in state MUST be the AIMessage containing the tool call, and `escalate_ticket` MUST NOT have been called

### Requirement: Approval path resumes execution
When a paused graph receives engineer approval, the caller SHALL resume the graph by
invoking it with `None` as the input and the same thread config. The `sensitive_tools`
node MUST then execute `escalate_ticket`, and the agent MUST continue to completion.

#### Scenario: Approve escalation
- **GIVEN** a graph paused before `sensitive_tools` with an `escalate_ticket` tool call pending
- **WHEN** the graph is resumed with `None` input and the same thread config
- **THEN** `escalate_ticket` MUST execute and return a result, and the graph MUST proceed to the next agent step

### Requirement: Rejection path injects refusal and resumes
When a paused graph receives engineer rejection, the caller SHALL inject a `ToolMessage`
with content `"Rejected by engineer: <reason>"` via `graph.update_state(as_node="sensitive_tools")`
and then resume with `None` input. The agent MUST receive the rejection message and MUST
NOT execute `escalate_ticket`.

#### Scenario: Reject escalation
- **GIVEN** a graph paused before `sensitive_tools` with an `escalate_ticket` tool call pending
- **WHEN** the caller injects a rejection `ToolMessage` via `update_state` and resumes with `None`
- **THEN** `escalate_ticket` MUST NOT have been called, the rejection message MUST appear in state, and the agent MUST process the rejection and terminate

### Requirement: Paused state persists across restarts
A paused graph thread MUST survive process restarts when the `PostgresSaver` checkpointer
is used. A new process MUST be able to resume or reject the same thread by referencing
its `thread_id` after restart.

#### Scenario: Resume after simulated restart
- **GIVEN** a graph thread paused before `sensitive_tools` with `PostgresSaver` checkpointer
- **WHEN** a new invocation references the same `thread_id` with `None` input
- **THEN** the graph MUST resume from the paused interrupt point and complete normally
