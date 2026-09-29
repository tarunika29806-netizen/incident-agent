import json
import pytest
from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

import agent
from agent import (
    extract_text,
    query_service_health,
    search_remediation_runbooks,
    get_agent_app,
    create_connection_pool,
    route_tools,
    SAFE_TOOLS,
    SENSITIVE_TOOLS,
    escalate_ticket,
    AgentState,
)


def test_extract_text_variants():
    """Test text normalization helper across string, list, and dict inputs."""
    assert extract_text("plain text") == "plain text"
    assert extract_text(["hello", "world"]) == "hello world"
    assert extract_text([{"text": "part 1"}, {"text": "part 2"}]) == "part 1 part 2"
    assert extract_text({"text": "dict text"}) == "dict text"


def test_query_service_health():
    """Test health check tool returns expected mock metrics for degraded and healthy services."""
    auth_health = json.loads(query_service_health.invoke({"service_name": "auth"}))
    assert auth_health["status"] == "degraded"
    assert "Redis session store" in auth_health["notes"]

    unknown_health = json.loads(query_service_health.invoke({"service_name": "unknown_svc"}))
    assert unknown_health["status"] == "healthy"
    assert unknown_health["cpu_percent"] == 15.0


def test_search_remediation_runbooks_mocked(mocker):
    """Test runbook search tool with mocked Gemini embedding and Postgres vector query."""
    mocker.patch.dict("os.environ", {
        "GEMINI_API_KEY": "test-key",
        "DATABASE_URL": "postgresql://localhost:5432/testdb"
    })

    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.embeddings = [MagicMock(values=[0.1] * 768)]
    mock_client.models.embed_content.return_value = mock_res
    mocker.patch("google.genai.Client", return_value=mock_client)

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [
        (1, "Auth timeout runbook", {"title": "Auth 504"}, 0.95),
        (2, "DB latency runbook", {"title": "DB Latency"}, 0.82)
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn
    mocker.patch("psycopg.connect", return_value=mock_conn)
    mocker.patch("pgvector.psycopg.register_vector")

    results_json = search_remediation_runbooks.invoke({"query": "auth 504 timeout"})
    results = json.loads(results_json)

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["title"] if "title" in results[0] else results[0]["metadata"]["title"] == "Auth 504"
    assert results[0]["similarity"] == 0.95


def test_connection_pool_configuration():
    """Test ConnectionPool is created with pooler compatible settings."""
    pool = create_connection_pool("postgresql://user:pass@localhost:6543/postgres")
    assert pool.max_size == 10


def test_agent_graph_execution_and_thread_persistence(mocker):
    """Test LangGraph safe tool loop routing and thread persistence using MemorySaver."""
    memory_checkpointer = MemorySaver()
    app = get_agent_app(checkpointer=memory_checkpointer, interrupt_before=[])

    # Sequence of mock LLM responses: 1st call emits tool_call, 2nd call emits final response
    tool_call_msg = AIMessage(
        content="Checking auth health...",
        tool_calls=[{
            "name": "query_service_health",
            "args": {"service_name": "auth"},
            "id": "call_auth_1"
        }]
    )
    final_ai_msg = AIMessage(content="Auth service is degraded due to high memory usage. Recommended remediation: restart auth pods.")

    mock_llm_instance = MagicMock()
    mock_bound_llm = MagicMock()
    mock_bound_llm.invoke.side_effect = [tool_call_msg, final_ai_msg]
    mock_llm_instance.bind_tools.return_value = mock_bound_llm

    with patch("agent.ChatGoogleGenerativeAI", return_value=mock_llm_instance):
        config = {"configurable": {"thread_id": "test-thread-42"}}
        initial_input = {"messages": [HumanMessage(content="Auth service is timing out")]}

        result = app.invoke(initial_input, config=config)

        assert "messages" in result
        # Verify initial human message + AIMessage(tool_call) + ToolMessage + AIMessage(final)
        messages = result["messages"]
        assert len(messages) >= 3

        # Check thread state persistence in checkpointer
        state_snapshot = app.get_state(config)
        assert state_snapshot is not None
        assert state_snapshot.values["summary"] != ""


# ---------------------------------------------------------------------------
# Task 1.3: route_tools routing — safe-only and sensitive-only messages
# ---------------------------------------------------------------------------

def _make_state(tool_calls: list) -> AgentState:
    """Build a minimal AgentState with a single AIMessage containing the given tool_calls."""
    msg = AIMessage(content="", tool_calls=tool_calls)
    return AgentState(messages=[msg], requires_escalation=False, summary="")


def test_route_tools_safe_only():
    """route_tools returns 'safe_tools' when only safe tools are called (task 1.3)."""
    state = _make_state([{"name": "query_service_health", "args": {"service_name": "auth"}, "id": "c1"}])
    result = route_tools(state)
    assert result == "safe_tools", f"Expected 'safe_tools', got {result!r}"


def test_route_tools_sensitive_only():
    """route_tools returns 'sensitive_tools' when only escalate_ticket is called (task 1.3)."""
    state = _make_state([{"name": "escalate_ticket", "args": {"ticket_title": "auth down", "severity": "P1"}, "id": "c2"}])
    result = route_tools(state)
    assert result == "sensitive_tools", f"Expected 'sensitive_tools', got {result!r}"


def test_route_tools_no_calls():
    """route_tools returns END when the last message has no tool calls."""
    from langgraph.graph import END
    msg = AIMessage(content="Done.")
    state = AgentState(messages=[msg], requires_escalation=False, summary="")
    result = route_tools(state)
    assert result == END


# ---------------------------------------------------------------------------
# Task 1.4: mixed-call routing rule
# ---------------------------------------------------------------------------

def test_route_tools_mixed():
    """Any sensitive call in a mixed message routes the whole message to sensitive_tools (task 1.4)."""
    state = _make_state([
        {"name": "query_service_health", "args": {"service_name": "auth"}, "id": "c3"},
        {"name": "escalate_ticket", "args": {"ticket_title": "auth down", "severity": "P1"}, "id": "c4"},
    ])
    result = route_tools(state)
    assert result == "sensitive_tools", (
        f"Expected 'sensitive_tools' for mixed message, got {result!r}. "
        "Any sensitive call must gate the whole message."
    )


# ---------------------------------------------------------------------------
# Task 4.1: HITL pause
# ---------------------------------------------------------------------------

def _make_escalation_app(checkpointer):
    """Return a compiled graph with interrupt_before=['sensitive_tools']."""
    return get_agent_app(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])


def _mock_llm_escalate():
    """Return a mock LLM that emits one escalate_ticket tool call then a final message."""
    escalate_msg = AIMessage(
        content="Service is still degraded. Escalating.",
        tool_calls=[{
            "name": "escalate_ticket",
            "args": {"ticket_title": "Auth service degraded", "severity": "P1"},
            "id": "call_esc_1"
        }]
    )
    final_msg = AIMessage(content="Escalation submitted for approval.")
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.invoke.side_effect = [escalate_msg, final_msg]
    mock_llm.bind_tools.return_value = mock_bound
    return mock_llm


def test_hitl_pause():
    """Graph pauses before sensitive_tools; escalate_ticket is NOT called (task 4.1)."""
    checkpointer = MemorySaver()
    app = _make_escalation_app(checkpointer)
    config = {"configurable": {"thread_id": "hitl-pause-thread"}}

    mock_llm = _mock_llm_escalate()
    escalate_called = []

    def fake_escalate(title, severity):
        escalate_called.append((title, severity))
        return json.dumps({"ticket_id": "INC-TEST"})

    with patch("agent.ChatGoogleGenerativeAI", return_value=mock_llm):
        with patch.object(escalate_ticket, "func", side_effect=fake_escalate):
            result = app.invoke(
                {"messages": [HumanMessage(content="Auth service is degraded")]},
                config=config,
            )

    # Graph should have paused — result is the snapshot up to the interrupt
    state = app.get_state(config)
    last_msg = state.values["messages"][-1]

    # The last message must be the AIMessage with the escalate_ticket tool call
    assert hasattr(last_msg, "tool_calls") and last_msg.tool_calls, (
        "Expected last message to have tool_calls (paused at interrupt), got none"
    )
    assert last_msg.tool_calls[0]["name"] == "escalate_ticket"

    # escalate_ticket must NOT have executed
    assert not escalate_called, "escalate_ticket was called before approval — HITL gate failed"

    # The graph must have a next step (it is not done)
    assert state.next, "Expected graph to be paused with a pending next step"


# ---------------------------------------------------------------------------
# Task 4.2: HITL approve
# ---------------------------------------------------------------------------

def test_hitl_approve():
    """Resuming with None executes escalate_ticket and completes the graph (task 4.2)."""
    checkpointer = MemorySaver()
    app = _make_escalation_app(checkpointer)
    config = {"configurable": {"thread_id": "hitl-approve-thread"}}

    mock_llm = _mock_llm_escalate()
    escalate_called = []
    real_escalate = escalate_ticket.func

    def tracking_escalate(**kwargs):
        result = real_escalate(**kwargs)
        escalate_called.append(kwargs)
        return result

    with patch("agent.ChatGoogleGenerativeAI", return_value=mock_llm):
        # Step 1: invoke — will pause before sensitive_tools
        app.invoke(
            {"messages": [HumanMessage(content="Auth service is degraded")]},
            config=config,
        )

        # Step 2: approve — resume with None; escalate_ticket should now execute
        with patch.object(escalate_ticket, "func", side_effect=tracking_escalate):
            app.invoke(None, config=config)

    assert escalate_called, "escalate_ticket was NOT called after approval — resume failed"

    state = app.get_state(config)
    assert not state.next, "Graph should have completed after approval, but still has pending steps"


# ---------------------------------------------------------------------------
# Task 4.3: HITL reject
# ---------------------------------------------------------------------------

def test_hitl_reject():
    """Injecting a rejection ToolMessage prevents escalate_ticket from executing (task 4.3)."""
    checkpointer = MemorySaver()
    app = _make_escalation_app(checkpointer)
    config = {"configurable": {"thread_id": "hitl-reject-thread"}}

    mock_llm = _mock_llm_escalate()
    escalate_called = []

    def fake_escalate(**kwargs):
        escalate_called.append(kwargs)
        return json.dumps({"ticket_id": "INC-REJECTED"})

    with patch("agent.ChatGoogleGenerativeAI", return_value=mock_llm):
        # Step 1: invoke ? pauses before sensitive_tools
        app.invoke(
            {"messages": [HumanMessage(content="Auth service is degraded")]},
            config=config,
        )

        # Retrieve the pending tool call ID so we can inject a matching ToolMessage
        state = app.get_state(config)
        last_msg = state.values["messages"][-1]
        assert last_msg.tool_calls, "Expected a paused tool call to reject"
        pending_call_id = last_msg.tool_calls[0]["id"]

        # Inject rejection: one ToolMessage per pending sensitive call
        rejection_msg = ToolMessage(
            content="Rejected by engineer: not approved at this time",
            tool_call_id=pending_call_id,
        )
        app.update_state(
            config,
            {"messages": [rejection_msg]},
            as_node="sensitive_tools",
        )

        # Step 2: resume with None ? agent should see rejection and stop
        with patch.object(escalate_ticket, "func", side_effect=fake_escalate):
            app.invoke(None, config=config)

    # escalate_ticket must NOT have run
    assert not escalate_called, (
        "escalate_ticket was called despite rejection ? HITL gate failed"
    )

    # Rejection message must appear in final state
    final_state = app.get_state(config)
    all_messages = final_state.values["messages"]

    rejection_texts = [
        m.content
        for m in all_messages
        if isinstance(m, ToolMessage)
        and "Rejected by engineer" in str(m.content)
    ]

    assert rejection_texts, "Rejection ToolMessage not found in final state"
