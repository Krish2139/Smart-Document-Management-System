def test_frontend_index_serving(client):
    """Verify that root / serves index.html with all required navigation and views."""
    response = client.get("/")
    assert response.status_code == 200
    assert "SmartDoc" in response.text
    assert "page-dashboard" in response.text
    assert "page-documents" in response.text
    assert "page-upload" in response.text
    assert "page-categories" in response.text
    assert "page-activity" in response.text
    assert "page-settings" in response.text


def test_frontend_static_assets(client):
    """Verify that all CSS and JavaScript modules exist and are accessible."""
    static_files = [
        "/static/css/main.css",
        "/static/css/variables.css",
        "/static/css/layout.css",
        "/static/css/components.css",
        "/static/js/api.js",
        "/static/js/state.js",
        "/static/js/navigation.js",
        "/static/js/dashboard.js",
        "/static/js/documents.js",
        "/static/js/upload.js",
        "/static/js/categories.js",
        "/static/js/activity.js",
        "/static/js/settings.js",
        "/static/js/app.js",
    ]

    for file_path in static_files:
        res = client.get(file_path)
        assert res.status_code == 200, f"Failed to retrieve static asset: {file_path}"


def test_frontend_initial_auth_landing(client):
    """Verify that root / defaults to displaying the Sign In / Register landing page."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Ensure page-auth and sidebar-auth-link are present and set as default active view
    assert 'id="page-auth"' in html
    assert 'id="sidebar-auth-link"' in html
    assert 'class="page-view active" id="page-auth"' in html
    assert 'Sign In / Register' in html
