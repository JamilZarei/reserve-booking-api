"""Tests run against a separate database (reserve_test) that is rebuilt from the seed on every run."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402

TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/reserve_test"
os.environ["DATABASE_URL"] = TEST_DB_URL
subprocess.run([sys.executable, str(ROOT / "scripts" / "init_db.py")], check=True, env=os.environ,
               cwd=ROOT, capture_output=True)

settings.database_url = TEST_DB_URL
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORD = "Pass@1234"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, username: str) -> dict:
    r = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def guest(client):      # علی محمدی
    return login(client, "ali.mohammadi@reserve.test")


@pytest.fixture(scope="session")
def guest2(client):     # زهرا حسینی
    return login(client, "09351237846")


@pytest.fixture(scope="session")
def host(client):       # رضا احمدی — میزبان اقامتگاه‌های ۱، ۲، ۳
    return login(client, "reza.ahmadi@reserve.test")


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin@reserve.test")
