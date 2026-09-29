# Change: Add API and Gradio UI

## Why

Expose the incident triage agent through a FastAPI service and a Gradio web interface.
The API and UI SHALL share the same agent service layer so HITL approval and rejection
operate on the same LangGraph thread state.

## What Changes

- Add FastAPI endpoints for starting/continuing triage, approving escalation, and rejecting escalation.
- Add a health endpoint for deployment/runtime checks.
- Add a Gradio interface mounted on the FastAPI application.
- Expose thread ID, incident description, workflow state, approval/rejection controls,
  rejection reason, and agent log.
- Return explicit workflow states including `COMPLETED`, `AWAITING_APPROVAL`,
  `RESOLVED`, and `REJECTED_AND_RESUMED`.
- Return HTTP 400 when approval/rejection is requested without a pending approval.
- Keep the existing LangGraph checkpoint/thread state as the source of truth.

## Out of Scope

- Deployment configuration.
- Authentication/authorization.
- Changes to the underlying triage tools or HITL rules.
