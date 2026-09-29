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
    create_connection_pool
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
    app = get_agent_app(checkpointer=memory_checkpointer)

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
