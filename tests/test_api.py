from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat():
    mocked_result = {
        "thread_id": "api-test-thread",
        "status": "COMPLETED",
        "log": "[AIMessage] Incident resolved",
        "state": {},
    }

    with patch("app.triage", return_value=mocked_result) as mock_triage:
        response = client.post(
            "/chat",
            json={
                "thread_id": "api-test-thread",
                "incident_description": "Auth service is returning 504 errors",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    mock_triage.assert_called_once_with(
        "api-test-thread",
        "Auth service is returning 504 errors",
    )


def test_approve():
    mocked_result = {
        "thread_id": "api-approve-thread",
        "status": "RESOLVED",
        "log": "[ToolMessage] Escalation approved",
        "state": {},
    }

    with patch("app.approve", return_value=mocked_result) as mock_approve:
        response = client.post(
            "/approve",
            json={"thread_id": "api-approve-thread"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    mock_approve.assert_called_once_with("api-approve-thread")


def test_reject():
    mocked_result = {
        "thread_id": "api-reject-thread",
        "status": "REJECTED_AND_RESUMED",
        "log": "[ToolMessage] Rejected by engineer: maintenance window",
        "state": {},
    }

    with patch("app.reject", return_value=mocked_result) as mock_reject:
        response = client.post(
            "/reject",
            json={
                "thread_id": "api-reject-thread",
                "reason": "maintenance window",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED_AND_RESUMED"
    mock_reject.assert_called_once_with(
        "api-reject-thread",
        "maintenance window",
    )


def test_approve_without_pending_returns_400():
    with patch(
        "app.approve",
        side_effect=ValueError("No pending approval for this thread"),
    ):
        response = client.post(
            "/approve",
            json={"thread_id": "no-pending-thread"},
        )

    assert response.status_code == 400
    assert "No pending approval" in response.json()["detail"]


def test_reject_without_pending_returns_400():
    with patch(
        "app.reject",
        side_effect=ValueError("No pending approval for this thread"),
    ):
        response = client.post(
            "/reject",
            json={
                "thread_id": "no-pending-thread",
                "reason": "not approved",
            },
        )

    assert response.status_code == 400
    assert "No pending approval" in response.json()["detail"]


def test_chat_validation():
    response = client.post(
        "/chat",
        json={
            "thread_id": "",
            "incident_description": "",
        },
    )

    assert response.status_code == 422
