"""Base repository.

Abstract base class implementing the repository pattern for data persistence.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class BaseRepository(ABC, Generic[T, ID]):
    """Abstract base class for repositories.

    Defines standard CRUD operations that all repositories must implement.
    Repositories act as adapters between domain entities and persistence.

    Type Parameters:
        T: The domain entity type.
        ID: The identifier type (usually str or int).
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new entity.

        Args:
            entity: Domain entity to persist.

        Returns:
            The persisted entity (may have generated fields populated).

        Raises:
            RepositoryError: If persistence fails.
        """
        ...

    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> Optional[T]:
        """Retrieve an entity by its identifier.

        Args:
            entity_id: Unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_all(self) -> List[T]:
        """Retrieve all entities.

        Returns:
            List of all entities (may be empty).
        """
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: Entity with updated fields.

        Returns:
            The updated entity.

        Raises:
            RepositoryError: If entity not found or update fails.
        """
        ...

    @abstractmethod
    async def delete(self, entity_id: ID) -> None:
        """Delete an entity by its identifier.

        Args:
            entity_id: Unique identifier of the entity to delete.

        Raises:
            EntityNotFoundError: If entity not found.
            RepositoryError: If deletion fails.
        """
        ...

    @abstractmethod
    async def exists(self, entity_id: ID) -> bool:
        """Check if an entity exists.

        Args:
            entity_id: Unique identifier to check.

        Returns:
            True if entity exists, False otherwise.
        """
        ...
