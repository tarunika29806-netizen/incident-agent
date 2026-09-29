\# Gradio UI Specification



\## Incident Triage Interface



The UI provides controls for investigating an incident and handling a pending escalation.



\### Required fields



The interface must provide:



\- Thread ID

\- Incident Description

\- Trigger Triage

\- Approve Escalation

\- Reject Action

\- Rejection Reason

\- Workflow State

\- Agent Log



\### Trigger Triage



When the user provides a Thread ID and Incident Description and selects \*\*Trigger Triage\*\*, the UI invokes the same service layer used by the REST API.



The resulting workflow state and agent log are displayed.



\### Approve Escalation



Selecting \*\*Approve Escalation\*\* invokes the approval service for the supplied Thread ID.



If there is no pending approval, the UI displays an error rather than executing an action.



If Thread ID is empty, the UI must display an error and must not call the approval service.



\### Reject Action



Selecting \*\*Reject Action\*\* invokes the rejection service for the supplied Thread ID and Rejection Reason.



If there is no pending approval, the UI displays an error rather than executing an action.



If Thread ID is empty, the UI must display an error and must not call the rejection service.



If Rejection Reason is empty, the UI must display an error and must not call the rejection service.



\### Workflow State



The UI displays the current workflow status returned by the service layer.



Supported states include:



\- `COMPLETED`

\- `AWAITING\_APPROVAL`

\- `RESOLVED`

\- `REJECTED\_AND\_RESUMED`

\- `ERROR`



\### Agent Log



The UI displays the agent's workflow log as Markdown.

