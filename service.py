import os
import json

from langchain_core.messages import HumanMessage, ToolMessage

from agent import get_agent_app


# Shared application graph and PostgreSQL checkpointer.
_agent_app = None
_checkpointer_cm = None
_checkpointer = None


def get_app():
    """Return the shared compiled LangGraph application."""
    global _agent_app, _checkpointer_cm, _checkpointer

    if _agent_app is None:
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set"
            )

        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import Connection
        from psycopg.rows import dict_row

        # Direct PostgreSQL connection.
        # prepare_threshold=None avoids prepared-statement conflicts
        # with PostgreSQL connection poolers.
        _checkpointer_cm = Connection.connect(
            db_url,
            autocommit=True,
            prepare_threshold=None,
            row_factory=dict_row,
        )

        _checkpointer = PostgresSaver(_checkpointer_cm)

        _agent_app = get_agent_app(
            checkpointer=_checkpointer
        )

    return _agent_app


def _config(thread_id: str) -> dict:
    """Return the LangGraph configuration for a thread."""
    return {
        "configurable": {
            "thread_id": thread_id
        }
    }


def _workflow_state(state: dict) -> str:
    """Map LangGraph state to the public workflow status."""
    messages = state.get("messages", [])

    if messages:
        last_message = messages[-1]

        tool_calls = getattr(
            last_message,
            "tool_calls",
            None
        )

        if tool_calls:
            sensitive_names = {
                "escalate_ticket"
            }

            if any(
                call.get("name") in sensitive_names
                for call in tool_calls
            ):
                return "AWAITING_APPROVAL"

    if state.get("requires_escalation"):
        return "RESOLVED"

    return "COMPLETED"


def _agent_log(state: dict) -> str:
    """Convert graph messages into a readable agent log."""
    lines = []

    for message in state.get("messages", []):
        message_type = message.__class__.__name__

        content = getattr(
            message,
            "content",
            ""
        )

        if isinstance(content, list):
            content = " ".join(
                item.get("text", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in content
            )

        content = str(content).strip()

        if content:
            lines.append(
                f"[{message_type}] {content}"
            )

        tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if tool_calls:
            for call in tool_calls:
                lines.append(
                    f"[Tool Call] {call.get('name')}: "
                    f"{json.dumps(call.get('args', {}))}"
                )

    return "\n".join(lines)


def triage(
    thread_id: str,
    incident_description: str
) -> dict:
    """Start or continue incident triage for a thread."""
    app = get_app()
    config = _config(thread_id)

    app.invoke(
        {
            "messages": [
                HumanMessage(
                    content=incident_description
                )
            ]
        },
        config=config,
    )

    state = app.get_state(config).values

    return {
        "thread_id": thread_id,
        "status": _workflow_state(state),
        "log": _agent_log(state),
        "state": state,
    }


def _pending_approval(thread_id: str):
    """Return the pending sensitive tool call, if any."""
    app = get_app()
    config = _config(thread_id)

    state = app.get_state(config).values

    messages = state.get(
        "messages",
        []
    )

    if not messages:
        return None

    last_message = messages[-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        None
    ) or []

    for call in tool_calls:
        if call.get("name") == "escalate_ticket":
            return call

    return None


def approve(thread_id: str) -> dict:
    """Approve the pending sensitive action and resume the graph."""
    app = get_app()
    config = _config(thread_id)

    if _pending_approval(thread_id) is None:
        raise ValueError(
            "No pending approval for this thread"
        )

    # Approval resumes the interrupted graph.
    app.invoke(
        None,
        config=config
    )

    state = app.get_state(config).values

    return {
        "thread_id": thread_id,
        "status": "RESOLVED",
        "log": _agent_log(state),
        "state": state,
    }


def reject(
    thread_id: str,
    reason: str
) -> dict:
    """
    Reject the pending sensitive action.

    The rejection is recorded in the checkpointed state.
    We deliberately do NOT invoke the graph again because doing so
    would send execution back to the LLM and could cause another
    escalation attempt.
    """
    app = get_app()
    config = _config(thread_id)

    pending_call = _pending_approval(
        thread_id
    )

    if pending_call is None:
        raise ValueError(
            "No pending approval for this thread"
        )

    rejection = ToolMessage(
        content=f"Rejected by engineer: {reason}",
        tool_call_id=pending_call["id"],
    )

    app.update_state(
        config,
        {
            "messages": [
                rejection
            ],
            "requires_escalation": False,
        },
        as_node="sensitive_tools",
    )

    state = app.get_state(config).values

    return {
        "thread_id": thread_id,
        "status": "REJECTED_AND_RESUMED",
        "log": _agent_log(state),
        "state": state,
    }