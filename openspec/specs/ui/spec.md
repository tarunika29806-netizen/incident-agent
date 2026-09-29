# ui Specification

## Purpose
TBD - created by archiving change add-api-and-ui. Update Purpose after archive.

## Requirements

### Requirement: Gradio Incident Triage Interface

The application SHALL expose a Gradio interface mounted at the FastAPI root path.

The interface MUST provide controls and displays for:

- Thread ID
- Incident Description
- Trigger Triage
- Approve
- Reject
- Rejection Reason
- Workflow State
- Agent Log

#### Scenario: Trigger triage from UI

- **GIVEN** a thread ID and incident description
- **WHEN** the user triggers triage
- **THEN** the UI MUST call the shared triage service
- **AND** display the resulting workflow state and agent log

#### Scenario: Approve escalation from UI

- **GIVEN** the workflow state is `AWAITING_APPROVAL`
- **WHEN** the user selects Approve
- **THEN** the UI MUST resume the same thread
- **AND** display the resulting workflow state and agent log

#### Scenario: Reject escalation from UI

- **GIVEN** the workflow state is `AWAITING_APPROVAL`
- **AND** a rejection reason is provided
- **WHEN** the user selects Reject
- **THEN** the UI MUST resume the same thread with the rejection
- **AND** display `REJECTED_AND_RESUMED` and the updated agent log

### Requirement: Shared API and UI Service Layer

The FastAPI endpoints and Gradio interface SHALL use the same service-layer functions
for triage, approval, and rejection so that both interfaces operate on the same
LangGraph checkpoint state.

#### Scenario: API and UI share the same workflow state

- **GIVEN** a thread with an active LangGraph checkpoint
- **WHEN** triage is started through the API or UI
- **THEN** both interfaces MUST operate on the same thread state
- **AND** an approval or rejection from either interface MUST resume that same thread
