# Spec Delta

## MODIFIED Requirements

### Requirement: Graph pauses before sensitive tool execution

The LangGraph agent graph SHALL pause before executing a model message if ANY tool call in that message targets a sensitive action. When a model message contains one or more sensitive tool calls, the entire message SHALL be routed through the human approval gate before any sensitive tool executes.

#### Scenario: Pause on escalation tool call

- **GIVEN** the agent graph is configured with a human approval gate and the model emits an `escalate_ticket` tool call
- **WHEN** the graph processes the model message
- **THEN** graph execution MUST pause before the sensitive action executes
- **AND** `escalate_ticket` MUST NOT execute before approval

#### Scenario: Mixed safe and sensitive calls

- **GIVEN** the model returns both `query_service_health` and `escalate_ticket` tool calls in one message
- **WHEN** the graph processes the model message
- **THEN** execution MUST pause for human approval
- **AND** the sensitive `escalate_ticket` call MUST NOT execute before approval

### Requirement: Approval path resumes execution

When a paused graph receives engineer approval, the caller SHALL resume the graph using the same thread. All pending sensitive actions SHALL then be allowed to execute and the agent SHALL continue processing the message.

#### Scenario: Approve escalation

- **GIVEN** a graph is paused with an `escalate_ticket` tool call pending
- **WHEN** an engineer approves the pending action
- **THEN** the graph MUST resume
- **AND** `escalate_ticket` MUST execute
- **AND** the agent MUST continue processing the workflow

#### Scenario: Approval payload lists every pending sensitive call

- **GIVEN** a model message contains multiple sensitive tool calls
- **WHEN** the graph pauses for approval
- **THEN** the approval state MUST identify every pending sensitive tool call

### Requirement: Rejection path injects refusal and resumes

When a paused graph receives engineer rejection, the caller SHALL create a `ToolMessage` containing `"Rejected by engineer: <reason>"` for every pending sensitive tool call. The sensitive tools MUST NOT execute after rejection.

#### Scenario: Reject escalation

- **GIVEN** a graph is paused with an `escalate_ticket` tool call pending
- **WHEN** an engineer rejects the action with a reason
- **THEN** a rejection `ToolMessage` MUST be recorded for the pending tool call
- **AND** `escalate_ticket` MUST NOT execute

#### Scenario: Reject multiple pending sensitive calls

- **GIVEN** a paused model message contains multiple pending sensitive tool calls
- **WHEN** an engineer rejects the actions
- **THEN** each pending sensitive tool call MUST receive a `ToolMessage`
- **AND** no sensitive tool call MUST execute

### Requirement: Paused state persists across restarts

A paused graph thread MUST survive process restarts when persistent checkpointing is used. A new process MUST be able to resume or reject the same thread by referencing its `thread_id`.

#### Scenario: Resume after simulated restart

- **GIVEN** a graph thread is paused before sensitive tool execution
- **WHEN** a new invocation references the same `thread_id` with approval
- **THEN** the graph MUST resume from the paused state and continue normally

#### Scenario: Reject after simulated restart

- **GIVEN** a graph thread is paused before sensitive tool execution
- **WHEN** a new invocation references the same `thread_id` and rejects the pending actions
- **THEN** every pending sensitive action MUST receive a rejection
- **AND** no sensitive action MUST execute
