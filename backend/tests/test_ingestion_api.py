import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_token
from app.models.agent_run import AgentRun
from app.models.workspace import Workspace


def test_generate_ingestion_token_and_storage(client: TestClient, db):
    # 1. Signup user
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "sdk_user@example.com", "password": "SecurePassword123!"},
    )
    assert signup_res.status_code == 201
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial token status (should be false)
    status_res = client.get(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_token"] is False

    # 3. Generate token
    gen_res = client.post(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    raw_token = gen_data["token"]
    assert raw_token.startswith("agy_ingest_")
    assert len(raw_token) > 30

    # 4. SECURITY CHECK: Verify DB stores SHA-256 hash, NOT raw token (NFR-001)
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    assert ws.ingestion_token_hash is not None
    assert ws.ingestion_token_hash != raw_token
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert ws.ingestion_token_hash == expected_hash

    # 5. Check status endpoint now returns True
    status_res2 = client.get(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    assert status_res2.status_code == 200
    assert status_res2.json()["has_token"] is True


def test_ingest_run_with_valid_token_headers(client: TestClient, db):
    # Setup user and token
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "runner@example.com", "password": "SecurePassword123!"},
    )
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    gen_res = client.post(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    ingestion_token = gen_res.json()["token"]

    payload = {
        "name": "CustomDataExtractionAgent",
        "external_run_id": "ext-trace-001",
        "status": "error",
        "error_message": "ValueError: Invalid JSON output from tool 'scrape_html'",
        "latency_ms": 850.5,
        "total_tokens": 1400,
        "raw_trace": {
            "node": "extractor",
            "error_step": 3,
            "inputs": {"url": "https://example.com/data"},
        },
    }

    # 1. Test ingestion via X-Ingestion-Token header
    ingest_res = client.post(
        "/api/v1/ingest/run",
        json=payload,
        headers={"X-Ingestion-Token": ingestion_token},
    )
    assert ingest_res.status_code == 200
    data = ingest_res.json()
    assert data["source"] == "sdk"
    assert data["status"] == "error"
    assert data["external_run_id"] == "ext-trace-001"
    assert data["workspace_id"] == workspace_id
    assert data["is_duplicate"] is False
    assert "run_id" in data

    # Verify persisted record in DB
    run_record = db.query(AgentRun).filter(AgentRun.id == data["run_id"]).first()
    assert run_record is not None
    assert run_record.source == "sdk"
    assert run_record.status == "error"
    assert run_record.name == "CustomDataExtractionAgent"
    assert run_record.error_message == "ValueError: Invalid JSON output from tool 'scrape_html'"
    assert run_record.latency_ms == 850.5
    assert run_record.total_tokens == 1400
    assert run_record.raw_trace["node"] == "extractor"

    # 2. Test ingestion via Authorization: Bearer header
    payload_success = {
        "name": "QuickSummaryAgent",
        "external_run_id": "ext-trace-002",
        "status": "success",
        "raw_trace": {"steps": [{"step": 1, "done": True}]},
    }
    ingest_res_bearer = client.post(
        "/api/v1/ingest/run",
        json=payload_success,
        headers={"Authorization": f"Bearer {ingestion_token}"},
    )
    assert ingest_res_bearer.status_code == 200
    assert ingest_res_bearer.json()["status"] == "success"
    assert ingest_res_bearer.json()["source"] == "sdk"


def test_ingest_run_unauthorized_and_invalid_tokens(client: TestClient):
    payload = {
        "name": "TestAgent",
        "status": "error",
        "error_message": "Some error",
    }

    # 1. Missing token
    res1 = client.post("/api/v1/ingest/run", json=payload)
    assert res1.status_code == 401
    assert res1.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid / Non-existent token
    res2 = client.post(
        "/api/v1/ingest/run",
        json=payload,
        headers={"X-Ingestion-Token": "agy_ingest_fake_invalid_token_1234567890"},
    )
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "INVALID_INGESTION_TOKEN"


def test_token_revocation_and_rotation(client: TestClient):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "rotate_user@example.com", "password": "SecurePassword123!"},
    )
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate token 1
    t1_res = client.post(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    token1 = t1_res.json()["token"]

    # Verify token 1 works
    res_ok = client.post(
        "/api/v1/ingest/run",
        json={"name": "Run1", "status": "success"},
        headers={"X-Ingestion-Token": token1},
    )
    assert res_ok.status_code == 200

    # Rotate token -> generates token 2
    t2_res = client.post(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    token2 = t2_res.json()["token"]
    assert token2 != token1

    # Token 1 must now be rejected
    res_t1_fail = client.post(
        "/api/v1/ingest/run",
        json={"name": "Run2", "status": "success"},
        headers={"X-Ingestion-Token": token1},
    )
    assert res_t1_fail.status_code == 401

    # Token 2 must succeed
    res_t2_ok = client.post(
        "/api/v1/ingest/run",
        json={"name": "Run2", "status": "success"},
        headers={"X-Ingestion-Token": token2},
    )
    assert res_t2_ok.status_code == 200

    # Revoke token
    del_res = client.delete(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["has_token"] is False

    # Token 2 must now be rejected
    res_t2_revoked = client.post(
        "/api/v1/ingest/run",
        json={"name": "Run3", "status": "success"},
        headers={"X-Ingestion-Token": token2},
    )
    assert res_t2_revoked.status_code == 401


def test_idempotent_duplicate_external_run_id(client: TestClient, db):
    # Setup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "idempotent@example.com", "password": "SecurePassword123!"},
    )
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    gen_res = client.post(f"/api/v1/workspaces/{workspace_id}/ingestion-token", headers=headers)
    ingestion_token = gen_res.json()["token"]

    payload1 = {
        "name": "BillingAgent",
        "external_run_id": "charge-run-999",
        "status": "error",
        "error_message": "StripeTimeout",
        "latency_ms": 3000.0,
    }

    # Initial ingestion
    res1 = client.post(
        "/api/v1/ingest/run",
        json=payload1,
        headers={"X-Ingestion-Token": ingestion_token},
    )
    assert res1.status_code == 200
    run1 = res1.json()
    assert run1["is_duplicate"] is False
    run_id = run1["run_id"]

    # Re-ingest with updated details for same external_run_id
    payload2 = {
        "name": "BillingAgent",
        "external_run_id": "charge-run-999",
        "status": "error",
        "error_message": "StripeTimeout (retried twice)",
        "latency_ms": 6000.0,
    }
    res2 = client.post(
        "/api/v1/ingest/run",
        json=payload2,
        headers={"X-Ingestion-Token": ingestion_token},
    )
    assert res2.status_code == 200
    run2 = res2.json()
    assert run2["is_duplicate"] is True
    assert run2["run_id"] == run_id

    # Verify in DB: exactly ONE row exists
    runs = (
        db.query(AgentRun)
        .filter(
            AgentRun.workspace_id == workspace_id,
            AgentRun.external_run_id == "charge-run-999",
        )
        .all()
    )
    assert len(runs) == 1
    assert runs[0].error_message == "StripeTimeout (retried twice)"
    assert runs[0].latency_ms == 6000.0


def test_oversized_payload_rejected(client: TestClient):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "heavy@example.com", "password": "SecurePassword123!"},
    )
    auth_data = signup_res.json()
    token = auth_data["access_token"]
    workspace_id = auth_data["workspace"]["id"]

    gen_res = client.post(
        f"/api/v1/workspaces/{workspace_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_token = gen_res.json()["token"]

    # Create oversized payload (>5MB)
    huge_string = "x" * (5 * 1024 * 1024 + 1024)
    payload = {
        "name": "HugeTraceAgent",
        "status": "error",
        "raw_trace": {"dump": huge_string},
    }

    res = client.post(
        "/api/v1/ingest/run",
        json=payload,
        headers={"X-Ingestion-Token": ingestion_token},
    )
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_multi_tenant_workspace_isolation(client: TestClient):
    # User A
    user_a = client.post(
        "/api/v1/auth/signup",
        json={"email": "tenant_a@example.com", "password": "SecurePassword123!"},
    ).json()
    token_a = user_a["access_token"]
    ws_a_id = user_a["workspace"]["id"]
    ingest_token_a = client.post(
        f"/api/v1/workspaces/{ws_a_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["token"]

    # User B
    user_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "tenant_b@example.com", "password": "SecurePassword123!"},
    ).json()
    token_b = user_b["access_token"]
    ws_b_id = user_b["workspace"]["id"]

    # User B cannot access or modify User A's token
    forbidden_get = client.get(
        f"/api/v1/workspaces/{ws_a_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_get.status_code == 403

    forbidden_gen = client.post(
        f"/api/v1/workspaces/{ws_a_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_gen.status_code == 403

    # Ingest run with token A
    res = client.post(
        "/api/v1/ingest/run",
        json={"name": "TenantARun", "status": "error", "error_message": "Isolated Error"},
        headers={"X-Ingestion-Token": ingest_token_a},
    )
    assert res.status_code == 200
    assert res.json()["workspace_id"] == ws_a_id

    # Check Tenant A runs list: run is present
    runs_a = client.get(
        f"/api/v1/workspaces/{ws_a_id}/runs?sync=false",
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    assert len(runs_a) == 1
    assert runs_a[0]["name"] == "TenantARun"
    assert runs_a[0]["source"] == "sdk"

    # Check Tenant B runs list: run is NOT visible
    runs_b = client.get(
        f"/api/v1/workspaces/{ws_b_id}/runs?sync=false",
        headers={"Authorization": f"Bearer {token_b}"},
    ).json()
    assert len(runs_b) == 0


def test_root_ingest_endpoint_compatibility(client: TestClient):
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "root_compat@example.com", "password": "SecurePassword123!"},
    ).json()
    token = signup_res["access_token"]
    ws_id = signup_res["workspace"]["id"]

    ingest_token = client.post(
        f"/api/v1/workspaces/{ws_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["token"]

    # Direct /ingest/run call
    res = client.post(
        "/ingest/run",
        json={"name": "RootEndpointAgent", "status": "error"},
        headers={"X-Ingestion-Token": ingest_token},
    )
    assert res.status_code == 200
    assert res.json()["source"] == "sdk"
    assert res.json()["workspace_id"] == ws_id


def test_adversarial_status_normalization_and_inference(client: TestClient, db):
    # Setup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "norm_test@example.com", "password": "SecurePassword123!"},
    ).json()
    token = signup_res["access_token"]
    ws_id = signup_res["workspace"]["id"]

    ingest_token = client.post(
        f"/api/v1/workspaces/{ws_id}/ingestion-token",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["token"]

    # 1. Status 'FAILED' should normalize to 'error'
    res1 = client.post(
        "/api/v1/ingest/run",
        json={"name": "Agent1", "status": "FAILED"},
        headers={"X-Ingestion-Token": ingest_token},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "error"

    # 2. Status 'completed' should normalize to 'success'
    res2 = client.post(
        "/api/v1/ingest/run",
        json={"name": "Agent2", "status": "completed"},
        headers={"X-Ingestion-Token": ingest_token},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "success"

    # 3. Missing status with error_message present should infer 'error'
    res3 = client.post(
        "/api/v1/ingest/run",
        json={"name": "Agent3", "error_message": "Unexpected crash"},
        headers={"X-Ingestion-Token": ingest_token},
    )
    assert res3.status_code == 200
    assert res3.json()["status"] == "error"

    # 4. Empty payload dictionary should still be accepted with defaults
    res4 = client.post(
        "/api/v1/ingest/run",
        json={},
        headers={"X-Ingestion-Token": ingest_token},
    )
    assert res4.status_code == 200
    assert res4.json()["status"] == "unknown"

