# Spec Delta

## MODIFIED Requirements

### Requirement: Agent State Graph & Reasoning
The agent SHALL orchestrate triage using a LangGraph state machine. It SHALL receive an
incident complaint, execute health checks and runbook search, synthesize findings via
Gemini LLM reasoning, and output an incident report containing root cause diagnosis and
recommended remediation. If manual intervention is required **or the service remains
degraded after runbook review**, the agent SHALL call `escalate_ticket` to request
escalation. The `route_tools` router MUST inspect every tool call in the AI message; if
any call targets a sensitive tool, the entire message MUST be routed to `sensitive_tools`
so that no sensitive action can execute without passing through the HITL approval gate.
Every `escalate_ticket` call MUST NOT execute without engineer approval.
On approval, all pending sensitive tool calls MUST be executed. On rejection, a
`ToolMessage` response MUST be injected for every pending sensitive tool call.

#### Scenario: Self-Remediable Incident Triage
- **GIVEN** an incident complaint where health checks pass and runbook specifies self-remediation
- **WHEN** the LangGraph agent executes triage
- **THEN** it MUST output an incident report, set `requires_escalation: False`, and MUST NOT call `escalate_ticket`

#### Scenario: Escalation-Required Incident Triage
- **GIVEN** an incident complaint where a core service stays degraded and requires manual intervention
- **WHEN** the LangGraph agent executes triage with a mocked LLM that emits an `escalate_ticket` tool call
- **THEN** graph execution MUST pause before `sensitive_tools`, and `escalate_ticket` MUST NOT have been called until engineer approves

#### Scenario: Mixed Tool Call Routed Through HITL Gate
- **GIVEN** an AI message containing both a safe tool call and an `escalate_ticket` call
- **WHEN** `route_tools` inspects the message
- **THEN** it MUST route to `sensitive_tools` (not `safe_tools`), ensuring the sensitive call cannot execute without approval

## ADDED Requirements

### Requirement: System prompt instructs escalation on degraded services
The agent system prompt SHALL instruct the LLM to call `escalate_ticket` when manual
intervention is needed or the service remains degraded after runbook review.

#### Scenario: System prompt contains escalation instruction
- **GIVEN** the compiled agent graph
- **WHEN** the system prompt string is inspected
- **THEN** it MUST contain language directing the agent to escalate when manual intervention is needed or the service stays degraded
