## ADDED Requirements

### Requirement: Triage HTTP API

The application SHALL expose a FastAPI API for incident triage using the existing
LangGraph agent and checkpoint thread state.

#### Scenario: Start triage

- **GIVEN** a valid thread ID and incident description
- **WHEN** the client sends a POST request to `/chat`
- **THEN** the API MUST execute or resume triage for that thread
- **AND** return the current workflow state and agent log
- **AND** return `AWAITING_APPROVAL` when the graph pauses at the HITL approval gate
- **AND** return `COMPLETED` when triage finishes without a pending approval

#### Scenario: Approve pending escalation

- **GIVEN** a thread with a pending sensitive tool call
- **WHEN** the client sends a POST request to `/approve`
- **THEN** the API MUST resume the same thread
- **AND** execute the pending sensitive tool call
- **AND** return the updated workflow state and agent log

#### Scenario: Reject pending escalation

- **GIVEN** a thread with a pending sensitive tool call
- **WHEN** the client sends a POST request to `/reject` with a rejection reason
- **THEN** the API MUST inject a rejection ToolMessage into the same thread
- **AND** resume the graph
- **AND** return `REJECTED_AND_RESUMED` when the rejection has been processed

#### Scenario: No pending approval

- **GIVEN** a thread without a pending HITL approval
- **WHEN** the client sends `/approve` or `/reject`
- **THEN** the API MUST return HTTP 400

### Requirement: Application Health Endpoint

The application SHALL expose `GET /healthz` for runtime health checks.

#### Scenario: Healthy application

- **WHEN** `/healthz` is requested
- **THEN** it MUST return HTTP 200 with a healthy status response
