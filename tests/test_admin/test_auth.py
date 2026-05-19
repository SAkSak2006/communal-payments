import pytest

from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    authenticate_user,
)


def test_password_hashing():
    """Password should be hashed and verifiable."""
    password = "test_password_123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_create_and_decode():
    """JWT token should encode and decode correctly."""
    data = {"sub": "42", "role": "admin"}
    token = create_access_token(data)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_jwt_invalid_token():
    """Invalid token should return None."""
    payload = decode_access_token("invalid.token.here")
    assert payload is None


def test_jwt_empty_token():
    """Empty token should return None."""
    payload = decode_access_token("")
    assert payload is None


@pytest.mark.asyncio
async def test_authenticate_user_success(session, seed_data):
    """Valid credentials should return user."""
    user = await authenticate_user(session, "admin", "admin123")
    assert user is not None
    assert user.username == "admin"
    assert user.full_name == "Тест Админ"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(session, seed_data):
    """Wrong password should return None."""
    user = await authenticate_user(session, "admin", "wrong_password")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_unknown_user(session, seed_data):
    """Unknown username should return None."""
    user = await authenticate_user(session, "unknown_user", "admin123")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_inactive_user(session, seed_data):
    """Inactive user should not authenticate."""
    admin = seed_data["admin"]
    admin.is_active = False
    await session.commit()

    user = await authenticate_user(session, "admin", "admin123")
    assert user is None

    # Restore
    admin.is_active = True
    await session.commit()
