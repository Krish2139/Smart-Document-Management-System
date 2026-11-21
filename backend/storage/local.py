import os
from pathlib import Path
import uuid
from backend.storage.base import StorageProvider
from backend.config.settings import settings
from backend.utils.logger import logger


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider for Phase 1.
    Stores documents in the configured local directory.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageProvider initialized at: {self.base_dir}")

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and guard against directory traversal attacks."""
        target = (self.base_dir / relative_path).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    def save(self, content: bytes, filename: str, subfolder: str = "") -> str:
        """Store a file and return relative storage path."""
        return self.save_file(content=content, filename=filename, subfolder=subfolder)

    def get(self, file_path: str) -> bytes:
        """Retrieve binary content of file."""
        return self.get_file(file_path=file_path)

    def delete(self, file_path: str) -> bool:
        """Delete stored file."""
        return self.delete_file(file_path=file_path)

    def generate_download_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate download URL (for local storage, returns local API route)."""
        clean_path = self._resolve_safe_path(file_path)
        return f"/api/documents/download?file_path={clean_path.name}"

    def save_file(self, content: bytes, filename: str, subfolder: str = "") -> str:
        """Save file bytes to local filesystem and return relative storage path."""
        target_dir = (self.base_dir / subfolder).resolve() if subfolder else self.base_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        destination = target_dir / filename
        destination.write_bytes(content)

        relative_path = destination.relative_to(self.base_dir).as_posix()
        return relative_path

    def get_file(self, file_path: str) -> bytes:
        """Read and return file bytes from disk."""
        target = self._resolve_safe_path(file_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return target.read_bytes()

    def delete_file(self, file_path: str) -> bool:
        """Delete file from disk if present."""
        try:
            target = self._resolve_safe_path(file_path)
            if target.exists() and target.is_file():
                target.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists on disk."""
        try:
            target = self._resolve_safe_path(file_path)
            return target.exists() and target.is_file()
        except Exception:
            return False

    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        target = self._resolve_safe_path(file_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return target.stat().st_size

    def check_health(self) -> bool:
        """Test write, read, and delete capability in the local directory."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            test_probe = self.base_dir / f".health_check_{uuid.uuid4().hex}"
            test_probe.write_text("health_ok", encoding="utf-8")
            content = test_probe.read_text(encoding="utf-8")
            test_probe.unlink()
            return content == "health_ok"
        except Exception as e:
            logger.error(f"LocalStorage health check failed: {e}")
            return False
