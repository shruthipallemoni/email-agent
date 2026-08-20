"""
A basic test that checks: when we call /api/health, do we get back a
successful response with status "ok"?

This is our first automated test - it lets us (and later, tools like GitHub)
check the app still works correctly every time we make changes.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data


def test_root_returns_running_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"]
