import uuid


async def test_register_login_and_me(client):
    email = f"user-{uuid.uuid4()}@example.com"
    password = "password123"
    display_name = "Test User"

    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["token_type"] == "bearer"
    assert register_data["access_token"]
    assert register_data["refresh_token"]
    assert register_data["user"]["email"] == email
    assert register_data["user"]["display_name"] == display_name
    assert register_data["user"]["onboarding_complete"] is False

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    token = login_data["access_token"]

    me_response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["display_name"] == display_name


async def test_register_duplicate_email(client):
    email = f"dup-{uuid.uuid4()}@example.com"
    payload = {"email": email, "password": "password123", "display_name": "Dup User"}

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_invalid_credentials(client):
    response = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_me_without_token(client):
    response = await client.get("/users/me")
    assert response.status_code == 401
