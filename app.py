import os

import gradio as gr
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from service import triage, approve, reject


app = FastAPI(
    title="Autonomous Incident Triage Agent",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    incident_description: str = Field(..., min_length=1)


class ApprovalRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    approved: bool = True
    rejection_reason: str | None = None


class RejectionRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


@app.get("/healthz")
def healthz():
    return {"status": "healthy"}


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        return triage(
            request.thread_id,
            request.incident_description,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.post("/approve")
def approve_endpoint(request: ApprovalRequest):
    try:
        if not request.approved:
            reason = request.rejection_reason or "Rejected by engineer."
            return reject(request.thread_id, reason)

        return approve(request.thread_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.post("/reject")
def reject_endpoint(request: RejectionRequest):
    try:
        return reject(
            request.thread_id,
            request.reason,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


def ui_triage(thread_id: str, incident_description: str):
    if not thread_id.strip():
        return "ERROR", "Thread ID is required."

    if not incident_description.strip():
        return "ERROR", "Incident Description is required."

    try:
        result = triage(
            thread_id.strip(),
            incident_description.strip(),
        )
        return result["status"], result["log"]
    except Exception as exc:
        return "ERROR", str(exc)


def ui_approve(thread_id: str):
    if not thread_id.strip():
        return "ERROR", "Thread ID is required."

    try:
        result = approve(thread_id.strip())
        return result["status"], result["log"]
    except ValueError as exc:
        return "ERROR", str(exc)
    except Exception as exc:
        return "ERROR", str(exc)


def ui_reject(thread_id: str, reason: str):
    if not thread_id.strip():
        return "ERROR", "Thread ID is required."

    if not reason.strip():
        return "ERROR", "Rejection Reason is required."

    try:
        result = reject(
            thread_id.strip(),
            reason.strip(),
        )
        return result["status"], result["log"]
    except ValueError as exc:
        return "ERROR", str(exc)
    except Exception as exc:
        return "ERROR", str(exc)


with gr.Blocks(title="Incident Triage Agent") as demo:
    gr.Markdown("# Autonomous Incident Triage Agent")

    gr.Markdown(
        "Investigate an incident, review the workflow state, "
        "and approve or reject sensitive escalation actions."
    )

    with gr.Row():
        thread_id = gr.Textbox(
            label="Thread ID",
            value="demo-thread",
        )

        incident_description = gr.Textbox(
            label="Incident Description",
            placeholder=(
                "Example: Auth service is timing out. "
                "Escalate immediately."
            ),
            lines=3,
        )

    with gr.Row():
        trigger_button = gr.Button("Trigger Triage")
        approve_button = gr.Button("Approve Escalation")
        reject_button = gr.Button("Reject Action")

    rejection_reason = gr.Textbox(
        label="Rejection Reason",
        placeholder="Enter reason when rejecting an escalation",
        lines=2,
    )

    workflow_state = gr.Label(
        label="Workflow State",
        value="READY",
    )

    agent_log = gr.Markdown(
        label="Agent Log",
    )

    trigger_button.click(
        ui_triage,
        inputs=[thread_id, incident_description],
        outputs=[workflow_state, agent_log],
    )

    approve_button.click(
        ui_approve,
        inputs=[thread_id],
        outputs=[workflow_state, agent_log],
    )

    reject_button.click(
        ui_reject,
        inputs=[thread_id, rejection_reason],
        outputs=[workflow_state, agent_log],
    )


app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )