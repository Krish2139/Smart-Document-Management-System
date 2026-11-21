from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract Generic Repository interface.
    Decouples domain services from concrete data access technologies
    (e.g., SQLAlchemy/SQLite in Phase 1, DynamoDB/Boto3 in Phase 2).
    """

    @abstractmethod
    def create(self, entity_data: dict) -> T:
        """Create and persist a new entity."""
        pass

    @abstractmethod
    def get(self, entity_id: Any) -> Optional[T]:
        """Fetch a single entity by its primary key/identifier."""
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[T]:
        """Fetch all entities with pagination and optional filters."""
        pass

    @abstractmethod
    def update(self, entity_id: Any, update_data: dict) -> Optional[T]:
        """Update an existing entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """Delete an entity by its identifier."""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """Alias for get() to maintain backward compatibility."""
        pass

    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100, **kwargs) -> List[T]:
        """Alias for list() to maintain backward compatibility."""
        pass
