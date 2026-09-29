import os
import json
from typing import Annotated, Sequence
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import psycopg
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()


def extract_text(content: str | list | dict) -> str:
    """Normalizes string or list-structured model message content to a string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    text_parts.append(str(item["text"]))
                elif "content" in item:
                    text_parts.append(str(item["content"]))
        return " ".join(text_parts)
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        return str(content)
    return str(content)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    requires_escalation: bool
    summary: str


MOCK_SERVICE_METRICS = {
    "auth": {
        "status": "degraded",
        "cpu_percent": 88.5,
        "memory_percent": 92.1,
        "error_rate": "12.4%",
        "latency_ms": 5200,
        "notes": "Redis session store memory high, 504 timeouts on /auth/login"
    },
    "database": {
        "status": "degraded",
        "cpu_percent": 94.0,
        "memory_percent": 75.0,
        "error_rate": "5.1%",
        "latency_ms": 3100,
        "notes": "High query latency, lock contentions on pg_stat_activity"
    },
    "payments": {
        "status": "degraded",
        "cpu_percent": 60.0,
        "memory_percent": 55.0,
        "error_rate": "18.2%",
        "latency_ms": 8500,
        "notes": "502 Bad Gateway from primary payment provider API"
    }
}


@tool
def query_service_health(service_name: str) -> str:
    """Check the operational status and resource metrics of a target backend service (auth, database, payments)."""
    name = service_name.lower().strip()
    if name in MOCK_SERVICE_METRICS:
        return json.dumps({"service": name, **MOCK_SERVICE_METRICS[name]})
    return json.dumps({
        "service": name,
        "status": "healthy",
        "cpu_percent": 15.0,
        "memory_percent": 30.0,
        "error_rate": "0.0%",
        "latency_ms": 45,
        "notes": "Service functioning within normal parameters."
    })


@tool
def search_remediation_runbooks(query: str) -> str:
    """Search vector knowledge base for incident remediation runbooks matching the query."""
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    if not api_key or not db_url:
        return json.dumps({"error": "Missing GEMINI_API_KEY or DATABASE_URL configuration."})

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(
                output_dimensionality=768,
                task_type="RETRIEVAL_QUERY"
            )
        )
        if hasattr(res, 'embeddings') and res.embeddings:
            query_vector = list(res.embeddings[0].values)
        elif hasattr(res, 'embedding') and res.embedding:
            query_vector = list(res.embedding.values)
        else:
            return json.dumps({"error": "Failed to generate query embedding vector."})
    except Exception as err:
        try:
            embedder = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=api_key
            )
            query_vector = embedder.embed_query(query)
        except Exception as fallback_err:
            return json.dumps({"error": f"Embedding generation failed: {err} | Fallback: {fallback_err}"})

    try:
        from pgvector.psycopg import register_vector
        with psycopg.connect(db_url) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, content, metadata, (1 - (embedding <=> %s))::FLOAT AS similarity "
                    "FROM incident_docs ORDER BY embedding <=> %s ASC LIMIT 2;",
                    (query_vector, query_vector)
                )
                rows = cur.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r[0],
                        "content": r[1],
                        "metadata": r[2],
                        "similarity": round(float(r[3]), 4)
                    })
                return json.dumps(results)
    except Exception as db_err:
        return json.dumps({"error": f"Database search query failed: {db_err}"})


SAFE_TOOLS = [query_service_health, search_remediation_runbooks]

SYSTEM_PROMPT = (
    "You are an Autonomous Incident Triage Agent. "
    "When investigating an incident, always follow this workflow:\n"
    "1. Inspect service health using `query_service_health` for relevant services.\n"
    "2. Search remediation runbooks using `search_remediation_runbooks` for matching incident guidance.\n"
    "3. Synthesize your findings into a clear incident report detailing root cause, health metrics, "
    "and recommended remediation steps.\n"
    "Be concise, technical, and accurate."
)


def agent_node(state: AgentState):
    api_key = os.getenv("GEMINI_API_KEY", "mock-key")
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.2
    ).bind_tools(SAFE_TOOLS)

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm.invoke(messages)

    text_content = extract_text(response.content)
    requires_escalation = "escalat" in text_content.lower() or "degraded" in text_content.lower()

    return {
        "messages": [response],
        "requires_escalation": state.get("requires_escalation", False) or requires_escalation,
        "summary": text_content
    }


def route_next(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "safe_tools"
    return END


def create_connection_pool(db_url: str) -> ConnectionPool:
    """Creates ConnectionPool configured for Supabase Transaction Pooler (port 6543)."""
    return ConnectionPool(
        conninfo=db_url,
        max_size=10,
        kwargs={
            "autocommit": True,
            "connect_timeout": 15,
            "prepare_threshold": None
        }
    )


def get_agent_app(checkpointer=None):
    """Compiles the LangGraph incident triage state machine."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("safe_tools", ToolNode(SAFE_TOOLS))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", route_next, ["safe_tools", END])
    workflow.add_edge("safe_tools", "agent")

    return workflow.compile(checkpointer=checkpointer)
