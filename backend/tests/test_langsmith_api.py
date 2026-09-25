from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.encryption import decrypt_secret
from app.models.workspace import Workspace
from app.models.agent_run import AgentRun
from app.services.langsmith_client import (
    LangSmithAuthError,
    LangSmithConnectionError,
    LangSmithProjectNotFoundError,
    langsmith_service,
)


SAMPLE_RUNS = [
    {
        "external_run_id": "run-001-err",
        "name": "CustomerSupportAgent",
        "source": "langsmith",
        "status": "error",
        "error_message": "SchemaValidationError: output key 'action' was missing",
        "latency_ms": 342.5,
        "total_tokens": 1250,
        "raw_trace": {
            "id": "run-001-err",
            "name": "CustomerSupportAgent",
            "error": "SchemaValidationError: output key 'action' was missing",
            "inputs": {"query": "Where is my order?"},
            "outputs": None,
        },
    },
    {
        "external_run_id": "run-002-ok",
        "name": "OrderLookupAgent",
        "source": "langsmith",
        "status": "success",
        "error_message": None,
        "latency_ms": 115.0,
        "total_tokens": 420,
        "raw_trace": {
            "id": "run-002-ok",
            "name": "OrderLookupAgent",
            "inputs": {"order_id": "123"},
            "outputs": {"status": "shipped"},
        },
    },
]


def test_normalize_run_unit():
    raw_error_run = {
        "id": "ext-123",
        "name": "PlannerAgent",
        "error": "ToolExecutionError: tool failed",
        "start_time": "2026-09-25T10:00:00.000Z",
        "end_time": "2026-09-25T10:00:01.500Z",
        "extra": {"token_usage": {"total_tokens": 500}},
    }
    normalized = langsmith_service.normalize_run(raw_error_run)
    assert normalized["external_run_id"] == "ext-123"
    assert normalized["name"] == "PlannerAgent"
    assert normalized["status"] == "error"
    assert "ToolExecutionError" in normalized["error_message"]
    assert normalized["latency_ms"] == 1500.0
    assert normalized["total_tokens"] == 500

    raw_success_run = {
        "id": "ext-456",
        "name": "SummaryAgent",
        "start_time": "2026-09-25T10:00:00.000Z",
        "end_time": "2026-09-25T10:00:00.250Z",
        "status": "success",
    }
    norm_success = langsmith_service.normalize_run(raw_success_run)
    assert norm_success["status"] == "success"
    assert norm_success["error_message"] is None


def test_connect_langsmith_success(client: TestClient, db):
    # 1. Signup user
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "ls_user@example.com", "password": "SecurePassword123!"},
    )
    assert signup_res.status_code == 201
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock LangSmith service
    with patch.object(langsmith_service, "validate_credentials", new_callable=AsyncMock) as mock_val, \
         patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_val.return_value = True
        mock_fetch.return_value = SAMPLE_RUNS

        payload = {
            "langsmith_key": "lsv2_pt_valid_secret_key_9876543210",
            "project": "agentic-ops-prod",
        }
        res = client.put(f"/api/v1/workspaces/{workspace_id}/langsmith", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["project"] == "agentic-ops-prod"
        assert data["workspace_id"] == workspace_id
        # SECURITY CHECK: API Key must NEVER be returned in response!
        assert "langsmith_key" not in data
        assert "langsmith_key_encrypted" not in data
        assert "secret" not in str(data).lower()

    # 3. Verify DB record: key is encrypted at rest and project is set
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    assert ws.langsmith_project == "agentic-ops-prod"
    assert ws.langsmith_key_encrypted is not None
    assert ws.langsmith_key_encrypted != payload["langsmith_key"]
    # Verify it can be decrypted back to plaintext
    decrypted = decrypt_secret(ws.langsmith_key_encrypted)
    assert decrypted == payload["langsmith_key"]

    # 4. Verify GET /workspaces/{id} does not leak key
    ws_res = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert ws_data["langsmith_connected"] is True
    assert ws_data["langsmith_project"] == "agentic-ops-prod"
    assert "langsmith_key" not in ws_data
    assert "langsmith_key_encrypted" not in ws_data


def test_connect_langsmith_invalid_key(client: TestClient):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "bad_key_user@example.com", "password": "SecurePassword123!"},
    )
    token = signup_res.json()["access_token"]
    workspace_id = signup_res.json()["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(langsmith_service, "validate_credentials", new_callable=AsyncMock) as mock_val:
        mock_val.side_effect = LangSmithAuthError("Invalid LangSmith API key or unauthorized project")

        payload = {
            "langsmith_key": "lsv2_pt_invalid_key_0000000000",
            "project": "agentic-ops-prod",
        }
        res = client.put(f"/api/v1/workspaces/{workspace_id}/langsmith", json=payload, headers=headers)
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "LANGSMITH_AUTH_FAILED"
        assert "Invalid LangSmith API key" in data["error"]["message"]


def test_connect_langsmith_unreachable(client: TestClient):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "unreachable_user@example.com", "password": "SecurePassword123!"},
    )
    token = signup_res.json()["access_token"]
    workspace_id = signup_res.json()["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(langsmith_service, "validate_credentials", new_callable=AsyncMock) as mock_val:
        mock_val.side_effect = LangSmithConnectionError("Unable to reach LangSmith API")

        payload = {
            "langsmith_key": "lsv2_pt_some_key_1111111111",
            "project": "agentic-ops-prod",
        }
        res = client.put(f"/api/v1/workspaces/{workspace_id}/langsmith", json=payload, headers=headers)
        assert res.status_code == 502
        data = res.json()
        assert data["error"]["code"] == "LANGSMITH_UNREACHABLE"


def test_langsmith_cross_tenant_forbidden(client: TestClient):
    # User A
    uA = client.post(
        "/api/v1/auth/signup",
        json={"email": "userA@example.com", "password": "SecurePassword123!"},
    ).json()
    ws_A_id = uA["workspace"]["id"]

    # User B
    uB = client.post(
        "/api/v1/auth/signup",
        json={"email": "userB@example.com", "password": "SecurePassword123!"},
    ).json()
    tokenB = uB["access_token"]
    headersB = {"Authorization": f"Bearer {tokenB}"}

    # User B attempts to configure LangSmith on Workspace A
    res = client.put(
        f"/api/v1/workspaces/{ws_A_id}/langsmith",
        json={"langsmith_key": "lsv2_pt_key_test_12345", "project": "proj"},
        headers=headersB,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # User B attempts to read runs from Workspace A
    res_runs = client.get(f"/api/v1/workspaces/{ws_A_id}/runs", headers=headersB)
    assert res_runs.status_code == 403
    assert res_runs.json()["error"]["code"] == "FORBIDDEN"


def test_list_runs_and_filter_by_status(client: TestClient, db):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "runs_filter_user@example.com", "password": "SecurePassword123!"},
    )
    token = signup_res.json()["access_token"]
    workspace_id = signup_res.json()["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Connect with mock runs
    with patch.object(langsmith_service, "validate_credentials", new_callable=AsyncMock) as mock_val, \
         patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_val.return_value = True
        mock_fetch.return_value = SAMPLE_RUNS

        client.put(
            f"/api/v1/workspaces/{workspace_id}/langsmith",
            json={"langsmith_key": "lsv2_pt_valid_secret_key_1111", "project": "test-filter-proj"},
            headers=headers,
        )

    # 1. Fetch all runs
    with patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = SAMPLE_RUNS
        res_all = client.get(f"/api/v1/workspaces/{workspace_id}/runs", headers=headers)
        assert res_all.status_code == 200
        runs_all = res_all.json()
        assert len(runs_all) == 2

    # 2. Fetch error runs only (REQ-003 acceptance criterion: filterable by error status)
    with patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = SAMPLE_RUNS
        res_error = client.get(f"/api/v1/workspaces/{workspace_id}/runs?status=error", headers=headers)
        assert res_error.status_code == 200
        runs_error = res_error.json()
        assert len(runs_error) == 1
        assert runs_error[0]["status"] == "error"
        assert runs_error[0]["external_run_id"] == "run-001-err"
        assert "SchemaValidationError" in runs_error[0]["error_message"]

    # 3. Fetch success runs only
    with patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = SAMPLE_RUNS
        res_success = client.get(f"/api/v1/workspaces/{workspace_id}/runs?status=success", headers=headers)
        assert res_success.status_code == 200
        runs_success = res_success.json()
        assert len(runs_success) == 1
        assert runs_success[0]["status"] == "success"
        assert runs_success[0]["external_run_id"] == "run-002-ok"


def test_disconnect_langsmith(client: TestClient, db):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "disconnect_user@example.com", "password": "SecurePassword123!"},
    )
    token = signup_res.json()["access_token"]
    workspace_id = signup_res.json()["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(langsmith_service, "validate_credentials", new_callable=AsyncMock) as mock_val, \
         patch.object(langsmith_service, "fetch_runs", new_callable=AsyncMock) as mock_fetch:
        mock_val.return_value = True
        mock_fetch.return_value = []
        client.put(
            f"/api/v1/workspaces/{workspace_id}/langsmith",
            json={"langsmith_key": "lsv2_pt_valid_secret_key_2222", "project": "proj-to-disconnect"},
            headers=headers,
        )

    # Disconnect
    del_res = client.delete(f"/api/v1/workspaces/{workspace_id}/langsmith", headers=headers)
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["connected"] is False
    assert del_data["project"] is None

    # Check status
    st_res = client.get(f"/api/v1/workspaces/{workspace_id}/langsmith", headers=headers)
    assert st_res.status_code == 200
    assert st_res.json()["connected"] is False
