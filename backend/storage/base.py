from abc import ABC, abstractmethod
from typing import Optional


class StorageProvider(ABC):
    """
    Abstract interface for document file storage.
    Enables pluggable implementations: LocalFileSystem (Phase 1) and Amazon S3 (Phase 2).
    """

    @abstractmethod
    def save(self, content: bytes, filename: str, subfolder: str = "") -> str:
        """Store a file and return its stored relative path or identifier."""
        pass

    @abstractmethod
    def get(self, file_path: str) -> bytes:
        """Retrieve raw binary content of a stored file."""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete a stored file. Returns True if deleted or already absent."""
        pass

    @abstractmethod
    def generate_download_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate a presigned or direct download URL for the file."""
        pass

    @abstractmethod
    def save_file(self, content: bytes, filename: str, subfolder: str = "") -> str:
        """Alias for save() to maintain backward compatibility."""
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        """Alias for get() to maintain backward compatibility."""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Alias for delete() to maintain backward compatibility."""
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check whether the file exists in storage."""
        pass

    @abstractmethod
    def get_file_size(self, file_path: str) -> int:
        """Return the size of the file in bytes."""
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """Verify that storage is accessible and write-capable."""
        pass
