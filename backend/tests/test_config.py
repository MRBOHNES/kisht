import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_jwt_secret_stops_startup(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_short_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_session_cookie_is_secure_by_default(monkeypatch):
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    assert Settings(_env_file=None).cookie_secure is True
