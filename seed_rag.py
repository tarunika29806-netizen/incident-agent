import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SAMPLE_RUNBOOKS = [
    {
        "title": "Auth Service 504 Gateway Timeout Remediation",
        "service": "auth",
        "content": (
            "Runbook for Auth Service 504 Gateway Timeouts. "
            "Symptoms: High latency, 504 Gateway Timeout errors on /auth/login and /auth/token endpoints. "
            "Investigation: Check Redis session store memory usage, inspect auth database connection pool metrics, check upstream dependency latency. "
            "Remediation: Flush expired session keys or restart auth pods if Redis memory > 90%; scale auth deployment replicas if CPU > 80%."
        )
    },
    {
        "title": "Database High Query Latency Remediation",
        "service": "database",
        "content": (
            "Runbook for Database High Query Latency. "
            "Symptoms: Database CPU utilization > 85%, connection pool exhaustion, slow query alert spikes. "
            "Investigation: Identify long-running queries via pg_stat_activity, check active lock contentions, inspect cache hit ratio. "
            "Remediation: Cancel blocking queries running > 30s using pg_cancel_backend(pid), verify missing index hints, scale transaction pooler max connections if connection ceiling reached."
        )
    },
    {
        "title": "Payment Gateway Integration Failures Remediation",
        "service": "payments",
        "content": (
            "Runbook for Payment Gateway Integration Failures. "
            "Symptoms: Payment processing returning 502/503 HTTP status, checkout drop-off rate spiking. "
            "Investigation: Check primary third-party payment provider status page, verify API keys and secret expiration, check egress network connectivity. "
            "Remediation: Switch primary traffic to secondary payment provider if primary provider error rate > 15%; enable fallback checkout mode and notify on-call billing lead."
        )
    }
]


def generate_embedding(text: str, api_key: str) -> list[float]:
    """Generates a 768-dimensional embedding using Gemini API."""
    models_to_try = ["gemini-embedding-001", "text-embedding-004"]
    last_err = None

    for model_name in models_to_try:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model=model_name,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            if hasattr(response, 'embeddings') and response.embeddings:
                return list(response.embeddings[0].values)
            elif hasattr(response, 'embedding') and response.embedding:
                return list(response.embedding.values)
        except Exception as err:
            last_err = err
            continue

    # Fallback to langchain_google_genai if google-genai fails
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embedder = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
        return embedder.embed_query(text)
    except Exception as fallback_err:
        raise RuntimeError(f"Failed to generate Gemini embedding: {last_err} | Fallback error: {fallback_err}")



def seed_database(db_url: str, runbooks_with_embeddings: list[dict]):
    """Idempotently seeds incident runbooks into Supabase incident_docs table."""
    import psycopg
    from pgvector.psycopg import register_vector

    with psycopg.connect(db_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS incident_docs (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    embedding VECTOR(768),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_incident_docs_title 
                ON incident_docs ((metadata->>'title'));
            """)

            upsert_query = """
                INSERT INTO incident_docs (content, metadata, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT ((metadata->>'title'))
                DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
            """

            for item in runbooks_with_embeddings:
                metadata_json = json.dumps({
                    "title": item["title"],
                    "service": item["service"]
                })
                cur.execute(
                    upsert_query,
                    (item["content"], metadata_json, item["embedding"])
                )

        conn.commit()


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if not db_url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print("Generating Gemini embeddings for sample runbooks...")
    seeded_data = []
    for runbook in SAMPLE_RUNBOOKS:
        print(f"Embedding: {runbook['title']}...")
        embedding = generate_embedding(runbook["content"], api_key)
        seeded_data.append({
            "title": runbook["title"],
            "service": runbook["service"],
            "content": runbook["content"],
            "embedding": embedding
        })

    print("Seeding runbooks into Postgres database...")
    seed_database(db_url, seeded_data)
    print("Successfully seeded 3 runbooks into incident_docs table.")


if __name__ == "__main__":
    main()
