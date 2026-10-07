import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.repositories.database import init_db
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

@pytest.mark.asyncio
async def test_password_hashing():
    pwd = "SuperSecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

@pytest.mark.asyncio
async def test_jwt_tokens():
    payload = {"sub": "user_123", "email": "test@example.com"}
    access_tok = create_access_token(payload)
    refresh_tok = create_refresh_token(payload)

    decoded_acc = decode_token(access_tok, expected_type="access")
    assert decoded_acc["sub"] == "user_123"
    assert decoded_acc["email"] == "test@example.com"
    assert decoded_acc["type"] == "access"

    decoded_ref = decode_token(refresh_tok, expected_type="refresh")
    assert decoded_ref["sub"] == "user_123"
    assert decoded_ref["type"] == "refresh"

    # Mismatched token types should raise error
    with pytest.raises(Exception):
        decode_token(access_tok, expected_type="refresh")

@pytest.mark.asyncio
async def test_auth_api_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"dev_{uuid.uuid4().hex[:8]}@company.io".lower()
        test_pwd = "SecureP@ssword2026"
        test_name = "Alex Developer"

        # 1. Register new user
        reg_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_pwd,
            "full_name": test_name
        })
        assert reg_res.status_code == 201, reg_res.text
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        assert "refresh_token" in reg_data
        assert reg_data["token_type"] == "bearer"
        assert reg_data["user"]["email"] == test_email
        assert reg_data["user"]["full_name"] == test_name
        user_id = reg_data["user"]["id"]

        # 2. Duplicate registration should fail
        dup_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": "AnotherPassword123",
            "full_name": "Copy Cat"
        })
        assert dup_res.status_code == 400
        assert "already exists" in dup_res.json()["detail"]

        # 3. Login with wrong password should fail
        bad_login = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": "IncorrectPassword"
        })
        assert bad_login.status_code == 401

        # 4. Login with correct password
        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_pwd
        })
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["user"]["id"] == user_id
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # 5. Access /api/auth/me with Bearer token
        me_res = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == test_email
        assert me_data["full_name"] == test_name

        # 6. Access /api/auth/me without token should fail
        unauth_res = await client.get("/api/auth/me")
        assert unauth_res.status_code == 401

        # 7. Access /api/auth/me with invalid token should fail
        invalid_res = await client.get("/api/auth/me", headers={
            "Authorization": "Bearer not-a-valid-token-string"
        })
        assert invalid_res.status_code == 401

        # 8. Refresh access token
        refresh_res = await client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_res.status_code == 200
        refreshed_data = refresh_res.json()
        assert "access_token" in refreshed_data
        new_access = refreshed_data["access_token"]

        # 10. Registration with invalid email format should fail with 422
        bad_email_res = await client.post("/api/auth/register", json={
            "email": "not-a-valid-email",
            "password": "ValidPassword123"
        })
        assert bad_email_res.status_code == 422

        # 11. Registration with password too short should fail with 422
        short_pwd_res = await client.post("/api/auth/register", json={
            "email": "valid@email.com",
            "password": "123"
        })
        assert short_pwd_res.status_code == 422

        # 12. Login with unregistered email should fail with 401
        unknown_email_res = await client.post("/api/auth/login", json={
            "email": "nonexistent_user_999@example.com",
            "password": "SomePassword123"
        })
        assert unknown_email_res.status_code == 401

        # 13. Refresh token with access token (type mismatch) should fail with 401
        bad_type_refresh = await client.post("/api/auth/refresh", json={
            "refresh_token": access_token
        })
        assert bad_type_refresh.status_code == 401
