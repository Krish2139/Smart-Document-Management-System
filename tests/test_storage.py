import pytest
from pathlib import Path
from backend.storage.local import LocalStorageProvider


def test_storage_lifecycle(tmp_path):
    """Test full file storage lifecycle: save, check, get, size, delete."""
    storage = LocalStorageProvider(base_dir=str(tmp_path))

    # Health check
    assert storage.check_health() is True

    # Save file
    filename = "test_document.txt"
    content = b"Smart Document Manager Test Payload"
    stored_path = storage.save_file(content=content, filename=filename, subfolder="invoices")

    # Verify exists
    assert storage.file_exists(stored_path) is True

    # Verify size
    assert storage.get_file_size(stored_path) == len(content)

    # Verify content read
    retrieved_content = storage.get_file(stored_path)
    assert retrieved_content == content

    # Delete file
    assert storage.delete_file(stored_path) is True
    assert storage.file_exists(stored_path) is False


def test_storage_path_traversal_prevention(tmp_path):
    """Ensure path traversal attempts are rejected."""
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Path traversal detected"):
        storage._resolve_safe_path("../../../etc/passwd")
