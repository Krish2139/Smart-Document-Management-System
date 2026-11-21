def test_get_categories(client):
    """Verify listing seeded categories with document count."""
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 6
    names = [c["name"] for c in data]
    assert "Academic" in names
    assert "Research" in names
    assert "Personal" in names
    assert "Projects" in names
    assert "Business" in names
    assert "Other" in names


def test_create_category(client):
    """Verify creating a new category."""
    payload = {
        "name": "Finance",
        "description": "Financial budgets, ledgers, and revenue projections",
        "color": "#10b981",
        "icon": "dollar-sign"
    }
    response = client.post("/api/categories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Finance"
    assert data["description"] == payload["description"]
    assert "id" in data


def test_create_duplicate_category(client):
    """Verify that creating duplicate category name returns 409 Conflict."""
    payload = {"name": "Finance", "description": "Duplicate finance"}
    response = client.post("/api/categories", json=payload)
    assert response.status_code == 409
    error_data = response.json()
    assert error_data["success"] is False
    assert error_data["error"]["code"] == "CONFLICT"


def test_update_category(client):
    """Verify updating category description and color."""
    cat_res = client.get("/api/categories")
    cat_id = next(c["id"] for c in cat_res.json() if c["name"] == "Finance")

    update_payload = {"description": "Updated financial accounts", "color": "#059669"}
    response = client.put(f"/api/categories/{cat_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated financial accounts"
    assert data["color"] == "#059669"


def test_delete_default_category_protection(client):
    """Verify that deleting the default 'Other' category is forbidden."""
    cat_res = client.get("/api/categories")
    other_cat_id = next(c["id"] for c in cat_res.json() if c["name"].lower() == "other")

    response = client.delete(f"/api/categories/{other_cat_id}")
    assert response.status_code == 400


def test_delete_custom_category(client):
    """Verify deleting a custom category."""
    cat_res = client.get("/api/categories")
    cat_id = next(c["id"] for c in cat_res.json() if c["name"] == "Finance")

    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True
