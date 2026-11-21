def test_get_settings(client):
    """Verify retrieving application and profile configuration."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "full_name" in data
    assert "email" in data
    assert data["auto_categorize"] is True
    assert data["duplicate_detection"] is True
    assert data["max_upload_size_mb"] == 20


def test_update_settings(client):
    """Verify updating configuration settings."""
    payload = {
        "full_name": "Chief Document Officer",
        "duplicate_detection": True,
        "max_upload_size_mb": 50
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Chief Document Officer"
    assert data["max_upload_size_mb"] == 50

    # Reset back to default 20 MB for subsequent test isolation
    reset_payload = {
        "full_name": "System Administrator",
        "email": "admin@smartdoc.local",
        "duplicate_detection": True,
        "max_upload_size_mb": 20
    }
    res_reset = client.put("/api/settings", json=reset_payload)
    assert res_reset.status_code == 200
    assert res_reset.json()["max_upload_size_mb"] == 20


def test_multi_user_profile_settings_isolation(client):
    """
    Ensure settings endpoint dynamically binds to the authenticated user's profile,
    so concurrent users see their own profile details rather than a shared global profile.
    """
    # 1. Register User Krish
    client.post("/api/auth/register", json={
        "username": "krish_settings_test",
        "email": "krish_settings@test.com",
        "password": "Password123!",
        "full_name": "Krish Patel"
    })
    krish_login = client.post("/api/auth/login", json={
        "username_or_email": "krish_settings_test",
        "password": "Password123!"
    })
    krish_token = krish_login.json()["access_token"]

    # 2. Register User Harsh
    client.post("/api/auth/register", json={
        "username": "harsh_settings_test",
        "email": "harsh_settings@test.com",
        "password": "Password123!",
        "full_name": "Harsh Patel"
    })
    harsh_login = client.post("/api/auth/login", json={
        "username_or_email": "harsh_settings_test",
        "password": "Password123!"
    })
    harsh_token = harsh_login.json()["access_token"]

    # 3. Krish retrieves settings -> sees Krish Patel
    krish_settings = client.get("/api/settings", headers={"Authorization": f"Bearer {krish_token}"})
    assert krish_settings.status_code == 200
    assert krish_settings.json()["full_name"] == "Krish Patel"
    assert krish_settings.json()["email"] == "krish_settings@test.com"

    # 4. Harsh retrieves settings -> sees Harsh Patel
    harsh_settings = client.get("/api/settings", headers={"Authorization": f"Bearer {harsh_token}"})
    assert harsh_settings.status_code == 200
    assert harsh_settings.json()["full_name"] == "Harsh Patel"
    assert harsh_settings.json()["email"] == "harsh_settings@test.com"

    # 5. Krish updates settings profile
    update_res = client.put(
        "/api/settings",
        headers={"Authorization": f"Bearer {krish_token}"},
        json={"full_name": "Krish Updated"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Krish Updated"

    # 6. Verify Harsh's settings profile is UNTOUCHED
    harsh_check = client.get("/api/settings", headers={"Authorization": f"Bearer {harsh_token}"})
    assert harsh_check.status_code == 200
    assert harsh_check.json()["full_name"] == "Harsh Patel"
    assert harsh_check.json()["email"] == "harsh_settings@test.com"


def test_concurrent_access_simulation(client):
    """Verify that multiple concurrent threads can query database without locking errors."""
    import concurrent.futures

    def hit_settings():
        res = client.get("/api/settings")
        return res.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(hit_settings) for _ in range(20)]
        results = [f.result() for f in futures]

    assert all(code == 200 for code in results)
