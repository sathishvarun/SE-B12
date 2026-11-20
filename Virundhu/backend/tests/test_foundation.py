"""Phase 1 foundation tests: health, public config, security helpers."""

import jwt
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.models import Base


def test_health_reports_database_and_redis(client):
    res = client.get("/health")
    assert res.status_code in (200, 503)
    body = res.json()
    assert set(body) == {"status", "database", "redis"}


def test_public_config_has_no_secrets(client):
    body = client.get("/api/v1/public/config").json()
    assert body["llm_provider"] in ("anthropic", "openai")
    assert "SECRET_KEY" not in str(body) and "api_key" not in str(body).lower()


def test_password_hashing_roundtrip():
    hashed = hash_password("Virundhu@123")
    assert hashed != "Virundhu@123"
    assert verify_password("Virundhu@123", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("anything", None)


def test_access_token_roundtrip_and_type_check():
    token = create_access_token(42)
    assert decode_access_token(token)["sub"] == "42"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "x")


def test_opaque_token_only_hash_is_stored():
    token, digest = new_opaque_token()
    assert digest == hash_token(token) and token not in digest and len(digest) == 64


def test_all_tables_registered():
    assert len(Base.metadata.tables) == 33  # + recoveries, meetings, agent runs, feedback, refunds, ai_usage
