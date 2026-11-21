from functools import lru_cache
from backend.config.settings import settings
from backend.storage.base import StorageProvider
from backend.storage.local import LocalStorageProvider


@lru_cache(maxsize=1)
def get_storage_provider() -> StorageProvider:
    """
    Factory function returning the configured storage provider.
    Defaults to LocalStorageProvider in Phase 1.
    """
    storage_type = settings.STORAGE_TYPE.lower()
    if storage_type == "local":
        return LocalStorageProvider(base_dir=settings.LOCAL_STORAGE_DIR)
    elif storage_type == "s3":
        # Phase 2 placeholder: will initialize S3StorageProvider
        raise NotImplementedError("S3StorageProvider will be implemented in Phase 2.")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


__all__ = ["StorageProvider", "LocalStorageProvider", "get_storage_provider"]
