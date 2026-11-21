def test_health_check_endpoint(client):
    """Verify that both /api/health and /api/v1/health return 200 and healthy components."""
    # Test /api/health
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["storage"]["status"] == "healthy"

    # Test /api/v1/health (versioned alias)
    v1_response = client.get("/api/v1/health")
    assert v1_response.status_code == 200
    assert v1_response.json()["status"] == "healthy"
