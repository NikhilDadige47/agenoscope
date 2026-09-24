from fastapi.testclient import TestClient


def test_signup_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@example.com", "password": "password1234"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert "id" in data["user"]
    assert "workspace" in data
    assert data["workspace"]["name"] == "alice's Workspace"
    assert data["workspace"]["owner_user_id"] == data["user"]["id"]


def test_signup_duplicate_email(client: TestClient):
    # First signup
    client.post(
        "/api/v1/auth/signup",
        json={"email": "duplicate@example.com", "password": "password1234"},
    )
    # Second signup with same email
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "duplicate@example.com", "password": "password5678"},
    )
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_signup_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "shortpw@example.com", "password": "123"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_signup_invalid_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "not-an-email", "password": "password1234"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_login_success(client: TestClient):
    # Create user
    client.post(
        "/api/v1/auth/signup",
        json={"email": "bob@example.com", "password": "securepassword123"},
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "bob@example.com"
    assert data["workspace"]["owner_user_id"] == data["user"]["id"]


def test_login_invalid_password(client: TestClient):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "carol@example.com", "password": "correctpassword1"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrongpassword99"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "anypassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_get_current_user_and_workspace(client: TestClient):
    # Signup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "david@example.com", "password": "password1234"},
    )
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch /auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == "david@example.com"
    assert me_data["workspace"]["owner_user_id"] == me_data["user"]["id"]

    # Fetch /workspaces/current
    ws_res = client.get("/api/v1/workspaces/current", headers=headers)
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert ws_data["name"] == "david's Workspace"
    assert ws_data["owner_user_id"] == me_data["user"]["id"]


def test_unauthenticated_request(client: TestClient):
    # No header
    res1 = client.get("/api/v1/auth/me")
    assert res1.status_code == 401
    assert res1.json()["error"]["code"] == "UNAUTHORIZED"

    # Malformed token
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "INVALID_TOKEN"


def test_workspace_isolation_cross_tenant_forbidden(client: TestClient):
    # Create User 1
    res1 = client.post(
        "/api/v1/auth/signup",
        json={"email": "user1@example.com", "password": "password1234"},
    )
    token1 = res1.json()["access_token"]
    ws1_id = res1.json()["workspace"]["id"]

    # Create User 2
    res2 = client.post(
        "/api/v1/auth/signup",
        json={"email": "user2@example.com", "password": "password1234"},
    )
    token2 = res2.json()["access_token"]
    ws2_id = res2.json()["workspace"]["id"]

    # User 1 accesses User 1's workspace -> 200 OK
    own_res = client.get(f"/api/v1/workspaces/{ws1_id}", headers={"Authorization": f"Bearer {token1}"})
    assert own_res.status_code == 200

    # User 2 attempts to access User 1's workspace -> 403 Forbidden (REQ-012 Data Isolation)
    forbidden_res = client.get(f"/api/v1/workspaces/{ws1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "FORBIDDEN"


def test_login_rate_limiting(client: TestClient):
    # Perform 10 requests which are allowed under 10/minute
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@example.com", "password": "wrongpassword"},
        )

    # 11th request should trigger 429
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@example.com", "password": "wrongpassword"},
    )
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "RATE_LIMITED"

