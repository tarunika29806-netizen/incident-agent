import pytest
from unittest.mock import MagicMock, patch
import seed_rag


def test_generate_embedding(mocker):
    """Test generating 768-dimensional embedding with mocked Gemini API client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = [MagicMock(values=[0.05] * 768)]
    mock_client.models.embed_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        embedding = seed_rag.generate_embedding("Test runbook content", "fake-key")
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert embedding[0] == 0.05


def test_seed_database_idempotent(mocker):
    """Test database seeding executes expected UPSERT SQL statements."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_conn.__enter__.return_value = mock_conn

    with patch("psycopg.connect", return_value=mock_conn), \
         patch("pgvector.psycopg.register_vector"):

        sample_data = [
            {
                "title": "Auth 504",
                "service": "auth",
                "content": "Auth timeout details",
                "embedding": [0.1] * 768
            },
            {
                "title": "DB Latency",
                "service": "database",
                "content": "DB latency details",
                "embedding": [0.2] * 768
            },
            {
                "title": "Payments Failure",
                "service": "payments",
                "content": "Payments failure details",
                "embedding": [0.3] * 768
            }
        ]

        seed_rag.seed_database("postgresql://localhost:5432/testdb", sample_data)

        assert mock_conn.commit.called
        # Check execute calls: 1 table create, 1 index create, 3 upserts
        assert mock_cur.execute.call_count == 5


def test_main_missing_env_vars(monkeypatch):
    """Test main script exits gracefully when environment variables are missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        seed_rag.main()
    assert exc_info.value.code == 1


def test_main_success_flow(monkeypatch, mocker):
    """Test main script orchestration when environment variables are provided."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/testdb")

    mock_gen_embed = mocker.patch("seed_rag.generate_embedding", return_value=[0.1] * 768)
    mock_seed_db = mocker.patch("seed_rag.seed_database")

    seed_rag.main()

    assert mock_gen_embed.call_count == 3
    assert mock_seed_db.call_count == 1
