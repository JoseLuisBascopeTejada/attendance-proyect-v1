def test_health_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "attendance-api"


def test_db_status_endpoint(client):
    resp = client.get("/api/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert "students" in data["tables"]
    assert "attendance" in data["tables"]
