import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repository import repository


@pytest.fixture
def client():
    repository.clear()
    with TestClient(app) as c:
        yield c
    repository.clear()


@pytest.fixture
def sheet(client):
    return client.post("/sheets", json={"name": "Budget", "rows": 50, "cols": 10}).json()
