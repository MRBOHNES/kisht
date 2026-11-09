import os
import subprocess

# must be set before app.config is imported
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://kisht:kisht@localhost:5432/kisht_test"
)
os.environ.setdefault("SEED_PASSWORD", "test-only-pass")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-0123")
# the test client talks plain http, which never sends Secure cookies
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
from httpx import ASGITransport, AsyncClient

from app.clock import current_time
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    subprocess.run(["alembic", "upgrade", "head"], check=True)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def set_now():
    """Pins the server clock for endpoints that take `current_time`."""
    def pin(at):
        app.dependency_overrides[current_time] = lambda: at
    yield pin
    app.dependency_overrides.pop(current_time, None)
