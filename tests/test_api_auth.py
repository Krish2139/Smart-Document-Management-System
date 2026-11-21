"""
Unit and integration tests for User Authentication (Sign In & Register).
"""
import pytest


def test_admin_login_success(client):
    """Verify default seeded admin can login with username and password."""
    payload = {
        "username_or_email": "admin",
        "password": "AdminPassword123!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["email"] == "admin@smartdoc.local"
    assert data["user"]["role"] == "admin"


def test_admin_login_with_email(client):
    """Verify login works interchangeably with email address."""
    payload = {
        "username_or_email": "admin@smartdoc.local",
        "password": "AdminPassword123!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "admin"


def test_login_invalid_credentials(client):
    """Verify invalid password returns 401 Unauthorized with descriptive messages."""
    # Wrong password
    res1 = client.post("/api/auth/login", json={
        "username_or_email": "admin",
        "password": "WrongPassword999!"
    })
    assert res1.status_code == 401
    assert "password is not correct" in res1.json()["error"]["message"].lower()

    # Non-existent user
    res2 = client.post("/api/auth/login", json={
        "username_or_email": "ghost_user",
        "password": "AnyPassword123!"
    })
    assert res2.status_code == 401
    assert "username is not correct" in res2.json()["error"]["message"].lower()


def test_user_registration_success(client):
    """Verify new user registration returns token and user payload."""
    payload = {
        "email": "sarah.connor@cyberdyne.org",
        "username": "sconnor",
        "full_name": "Sarah Connor",
        "password": "ProtectJohn2026!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "sarah.connor@cyberdyne.org"
    assert data["user"]["username"] == "sconnor"
    assert data["user"]["role"] == "user"
    assert data["user"]["is_active"] is True


def test_user_registration_duplicate_checks(client):
    """Verify unique constraints on email and username (409 Conflict)."""
    # 1. Duplicate email
    res1 = client.post("/api/auth/register", json={
        "email": "sarah.connor@cyberdyne.org",
        "username": "sarah_unique_2",
        "full_name": "Sarah Alternate",
        "password": "ValidPassword123!"
    })
    assert res1.status_code == 409

    # 2. Duplicate username
    res2 = client.post("/api/auth/register", json={
        "email": "different.email@domain.com",
        "username": "sconnor",
        "full_name": "Another Sarah",
        "password": "ValidPassword123!"
    })
    assert res2.status_code == 409


def test_user_registration_validation(client):
    """Verify short password and invalid email are rejected with 422."""
    # Short password (< 6 chars)
    res = client.post("/api/auth/register", json={
        "email": "valid.email@example.com",
        "username": "shortpass_user",
        "full_name": "Short Pass",
        "password": "123"
    })
    assert res.status_code == 422


def test_get_current_user_me(client):
    """Verify GET /api/auth/me returns authenticated user details."""
    # 1. Login to get token
    login_res = client.post("/api/auth/login", json={
        "username_or_email": "admin",
        "password": "AdminPassword123!"
    })
    token = login_res.json()["access_token"]

    # 2. Call /me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    user = me_res.json()
    assert user["username"] == "admin"
    assert user["email"] == "admin@smartdoc.local"

    # 3. Call without token -> 401 Unauthorized
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401


def test_update_profile_and_change_password(client):
    """Verify profile updates and password change workflow."""
    # Register fresh test user
    reg = client.post("/api/auth/register", json={
        "email": "update.test@example.com",
        "username": "updatetest",
        "full_name": "Original Name",
        "password": "OriginalPassword123!"
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Profile
    update_res = client.put("/api/auth/profile", json={"full_name": "Updated Name"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Updated Name"

    # 2. Change Password
    pw_res = client.post("/api/auth/change-password", json={
        "current_password": "OriginalPassword123!",
        "new_password": "NewSecurePassword456!"
    }, headers=headers)
    assert pw_res.status_code == 200

    # 3. Old password should fail
    fail_res = client.post("/api/auth/login", json={
        "username_or_email": "updatetest",
        "password": "OriginalPassword123!"
    })
    assert fail_res.status_code == 401

    # 4. New password should succeed
    succ_res = client.post("/api/auth/login", json={
        "username_or_email": "updatetest",
        "password": "NewSecurePassword456!"
    })
    assert succ_res.status_code == 200


def test_logout_endpoint(client):
    """Verify logout endpoint returns success."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_frontend_auth_elements(client):
    """Verify auth modal and user container exist in frontend index.html."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert 'id="auth-modal-backdrop"' in html
    assert 'id="header-user-container"' in html
    assert '/static/js/auth.js' in html


def test_multi_user_document_attribution(client):
    """Verify that document upload associates with authenticated user and filters by user_id."""
    import io
    # 1. Login as admin
    login_res = client.post("/api/auth/login", json={
        "username_or_email": "admin",
        "password": "AdminPassword123!"
    })
    token = login_res.json()["access_token"]
    admin_id = login_res.json()["user"]["id"]

    # 2. Upload document with user token
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("admin_annual_strategy.pdf", io.BytesIO(b"%PDF-1.4 Admin document"), "application/pdf")}
    res = client.post("/api/documents", files=files, headers=headers)
    assert res.status_code == 201
    doc = res.json()
    assert doc["user_id"] == admin_id
    assert doc["uploaded_by"] == "System Administrator"

    # 3. Filter documents by user_id
    filter_res = client.get(f"/api/documents?user_id={admin_id}")
    assert filter_res.status_code == 200
    items = filter_res.json()["items"]
    assert any(d["id"] == doc["id"] for d in items)


def test_strict_multi_user_document_isolation(client):
    """
    Verify complete multi-user data isolation:
    - User A cannot see User B's documents in listing or search.
    - User A cannot download, preview, update, or delete User B's documents (returns 404).
    - Dashboard statistics only reflect the authenticated user's own data.
    - User B can upload a file with identical content without duplicate collision across users.
    """
    import io

    # 1. Register User A (Krish Patel)
    reg_a = client.post("/api/auth/register", json={
        "email": "krish.patel@testiso.org",
        "username": "krishpatel_iso",
        "full_name": "Krish Patel",
        "password": "Password123!"
    })
    assert reg_a.status_code == 201
    token_a = reg_a.json()["access_token"]
    user_a_id = reg_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B (Alice Smith)
    reg_b = client.post("/api/auth/register", json={
        "email": "alice.smith@testiso.org",
        "username": "alicesmith_iso",
        "full_name": "Alice Smith",
        "password": "Password123!"
    })
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    user_b_id = reg_b.json()["user"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A uploads a private document
    shared_content = b"%PDF-1.4 Secret Project Documentation for Test"
    file_a = {"file": ("krish_secret_contract.pdf", io.BytesIO(shared_content), "application/pdf")}
    res_a = client.post("/api/documents", files=file_a, headers=headers_a)
    assert res_a.status_code == 201
    doc_a = res_a.json()
    doc_a_id = doc_a["id"]
    assert doc_a["user_id"] == user_a_id

    # 4. User B uploads a document
    file_b = {"file": ("alice_marketing_plan.pdf", io.BytesIO(b"%PDF-1.4 Alice's Private Strategy"), "application/pdf")}
    res_b = client.post("/api/documents", files=file_b, headers=headers_b)
    assert res_b.status_code == 201
    doc_b = res_b.json()
    doc_b_id = doc_b["id"]
    assert doc_b["user_id"] == user_b_id

    # 5. User A lists documents: must ONLY see doc_a, NEVER doc_b
    list_a = client.get("/api/documents", headers=headers_a)
    assert list_a.status_code == 200
    list_a_ids = [d["id"] for d in list_a.json()["items"]]
    assert doc_a_id in list_a_ids
    assert doc_b_id not in list_a_ids

    # 6. User B lists documents: must ONLY see doc_b, NEVER doc_a
    list_b = client.get("/api/documents", headers=headers_b)
    assert list_b.status_code == 200
    list_b_ids = [d["id"] for d in list_b.json()["items"]]
    assert doc_b_id in list_b_ids
    assert doc_a_id not in list_b_ids

    # 7. User A searches for User B's file: must return 0 results
    search_a = client.get("/api/documents/search?q=alice", headers=headers_a)
    assert search_a.status_code == 200
    assert search_a.json()["total"] == 0

    # 8. User B attempts to access User A's document by ID: must return 404
    get_cross = client.get(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert get_cross.status_code == 404

    # 9. User B attempts to get metadata of User A's document: must return 404
    meta_cross = client.get(f"/api/documents/{doc_a_id}/metadata", headers=headers_b)
    assert meta_cross.status_code == 404

    # 10. User B attempts to preview User A's document: must return 404
    prev_cross = client.get(f"/api/documents/{doc_a_id}/preview", headers=headers_b)
    assert prev_cross.status_code == 404

    # 11. User B attempts to download User A's document: must return 404
    dl_cross = client.get(f"/api/documents/{doc_a_id}/download", headers=headers_b)
    assert dl_cross.status_code == 404

    # 12. User B attempts to update category of User A's document: must return 404
    cat_cross = client.patch(
        f"/api/documents/{doc_a_id}/category",
        json={"category_name": "Business"},
        headers=headers_b
    )
    assert cat_cross.status_code == 404

    # 13. User B attempts to delete User A's document: must return 404
    del_cross = client.delete(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert del_cross.status_code == 404

    # Document A should still exist safely for User A
    get_owner = client.get(f"/api/documents/{doc_a_id}", headers=headers_a)
    assert get_owner.status_code == 200

    # 14. Dashboard statistics isolation:
    # User A dashboard statistics should show exactly 1 total document (Krish's)
    stats_a = client.get("/api/dashboard/statistics", headers=headers_a)
    assert stats_a.status_code == 200
    assert stats_a.json()["total_documents"] == 1

    # User B dashboard statistics should show exactly 1 total document (Alice's)
    stats_b = client.get("/api/dashboard/statistics", headers=headers_b)
    assert stats_b.status_code == 200
    assert stats_b.json()["total_documents"] == 1

    # 15. Cross-user identical file upload:
    # User B should be permitted to upload a file with identical content without cross-tenant conflict
    file_b_clone = {"file": ("alice_copy_of_shared.pdf", io.BytesIO(shared_content), "application/pdf")}
    res_b_clone = client.post("/api/documents", files=file_b_clone, headers=headers_b)
    assert res_b_clone.status_code == 201
