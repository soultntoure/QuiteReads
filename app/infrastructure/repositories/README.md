# Repositories

## Overview

This module provides concrete repository implementations for persisting domain entities using SQLAlchemy. It implements the Repository Pattern, acting as an adapter between domain entities and the PostgreSQL database.

## Purpose

- Provide abstract repository interface defining standard CRUD operations
- Implement experiment persistence with polymorphic type handling (centralized/federated)
- Implement metrics persistence with specialized queries for analysis
- Encapsulate all database access logic away from domain layer

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `base_repository.py` | Abstract repository interface | Generic `BaseRepository[T, ID]` with CRUD contract |
| `experiment_repository.py` | Experiment persistence | Handles `CentralizedExperiment` and `FederatedExperiment` |
| `metrics_repository.py` | Metrics persistence | Provides batch operations and aggregate queries |

---

## 1. base_repository.py

### Overview

Defines the abstract base class for all repositories, establishing a consistent CRUD interface that all concrete implementations must follow.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `T` | Type variable | Domain entity type |
| `ID` | Type variable | Identifier type (str or int) |
| `BaseRepository` | Abstract base class | Generic over entity and ID types |

### Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add` | `async def add(entity: T) -> T` | Persist a new entity |
| `get_by_id` | `async def get_by_id(entity_id: ID) -> Optional[T]` | Retrieve entity by identifier |
| `get_all` | `async def get_all() -> List[T]` | Retrieve all entities |
| `update` | `async def update(entity: T) -> T` | Update existing entity |
| `delete` | `async def delete(entity_id: ID) -> None` | Delete entity by identifier |
| `exists` | `async def exists(entity_id: ID) -> bool` | Check if entity exists |

### Usage Examples

```python
from app.infrastructure.repositories import BaseRepository

# All repositories inherit from BaseRepository
class MyRepository(BaseRepository[MyEntity, str]):
    async def add(self, entity: MyEntity) -> MyEntity:
        # Implementation
        ...
```

### Significance

This class enforces the **Dependency Inversion Principle** - domain layer depends on abstractions, not concrete implementations. The generic typing ensures type safety across different entity types.

---

## 2. experiment_repository.py

### Overview

Handles persistence of experiment domain entities, converting between domain entities (`CentralizedExperiment`, `FederatedExperiment`) and SQLAlchemy models. Supports polymorphic experiment types with proper serialization of configuration and metrics.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ExperimentRepository` | Experiment persistence | Extends `BaseRepository[Experiment, str]` |

### Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add` | `async def add(entity: Experiment) -> Experiment` | Persist new experiment with metrics |
| `get_by_id` | `async def get_by_id(entity_id: str) -> Optional[Experiment]` | Retrieve by UUID |
| `get_all` | `async def get_all() -> List[Experiment]` | Get all, ordered by created_at desc |
| `get_by_status` | `async def get_by_status(status: ExperimentStatus) -> List[Experiment]` | Filter by status |
| `get_by_type` | `async def get_by_type(experiment_type: str) -> List[Experiment]` | Filter by type |
| `get_by_status_and_type` | `async def get_by_status_and_type(...) -> List[Experiment]` | Combined filter |
| `update` | `async def update(entity: Experiment) -> Experiment` | Update with metrics refresh |
| `delete` | `async def delete(entity_id: str) -> None` | Delete experiment |
| `exists` | `async def exists(entity_id: str) -> bool` | Check existence |

### Private Methods

| Method | Purpose |
|--------|---------|
| `_to_model` | Convert domain entity to SQLAlchemy model |
| `_to_entity` | Convert SQLAlchemy model to domain entity |
| `_update_model` | Update model fields from entity |

### Usage Examples

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories import ExperimentRepository
from app.core.experiments import CentralizedExperiment
from app.utils.types import ExperimentStatus

async def example(session: AsyncSession):
    repo = ExperimentRepository(session)

    # Create experiment
    experiment = CentralizedExperiment(name="Test", config=config)
    await repo.add(experiment)

    # Retrieve by ID
    retrieved = await repo.get_by_id(experiment.experiment_id)

    # Query by status
    running = await repo.get_by_status(ExperimentStatus.RUNNING)

    # Query by type
    federated = await repo.get_by_type("federated")
```

### Significance

This repository handles the complexity of **polymorphic entity persistence**. It:
- Serializes `Configuration` to JSON dict
- Handles federated-specific fields (`n_clients`, `n_rounds`, `aggregation_strategy`)
- Manages bidirectional relationship with `MetricModel`
- Reconstructs proper entity subclass based on `experiment_type`

---

## 3. metrics_repository.py

### Overview

Handles persistence of performance metrics with specialized query capabilities for metrics analysis. Supports batch operations for efficient bulk inserts and provides aggregate statistics.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `MetricsRepository` | Metrics persistence | Extends `BaseRepository[PerformanceMetric, int]` |

### Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add` | `async def add(entity: PerformanceMetric) -> PerformanceMetric` | Persist single metric |
| `add_batch` | `async def add_batch(metrics: List[PerformanceMetric]) -> List[...]` | Bulk insert metrics |
| `get_by_id` | `async def get_by_id(entity_id: int) -> Optional[PerformanceMetric]` | Retrieve by primary key |
| `get_all` | `async def get_all() -> List[PerformanceMetric]` | Get all metrics |
| `get_by_experiment` | `async def get_by_experiment(experiment_id: str) -> List[...]` | All metrics for experiment |
| `get_by_experiment_and_name` | `async def get_by_experiment_and_name(...) -> List[...]` | Filter by name (rmse, loss) |
| `get_client_metrics` | `async def get_client_metrics(...) -> List[...]` | Client-specific metrics |
| `get_round_metrics` | `async def get_round_metrics(...) -> List[...]` | Round-specific metrics |
| `get_metric_stats` | `async def get_metric_stats(...) -> Optional[dict]` | Aggregate stats (min/max/avg) |
| `delete_by_experiment` | `async def delete_by_experiment(experiment_id: str) -> int` | Bulk delete by experiment |

### Usage Examples

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories import MetricsRepository
from app.core.metrics import PerformanceMetric

async def example(session: AsyncSession):
    repo = MetricsRepository(session)

    # Batch insert metrics
    metrics = [
        PerformanceMetric(name="rmse", value=0.85, experiment_id="abc-123", round_number=1),
        PerformanceMetric(name="rmse", value=0.82, experiment_id="abc-123", round_number=2),
    ]
    await repo.add_batch(metrics)

    # Get all RMSE values for experiment
    rmse_history = await repo.get_by_experiment_and_name("abc-123", "rmse")

    # Get aggregate statistics
    stats = await repo.get_metric_stats("abc-123", "rmse")
    # Returns: {"min": 0.82, "max": 0.85, "avg": 0.835, "count": 2}

    # Get client-specific metrics (federated)
    client_metrics = await repo.get_client_metrics("abc-123", "client_0")
```

### Significance

This repository provides **analytics-oriented queries** beyond basic CRUD:
- Efficient batch operations reduce database round-trips
- Aggregate functions (`min`, `max`, `avg`) computed at database level
- Metrics are treated as **immutable** (update raises `NotImplementedError`)
- Specialized queries support dashboard visualization needs

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Infrastructure (Adapters) |
| **Pattern** | Repository Pattern |
| **Dependencies** | `app.core` (domain entities), `app.infrastructure.models` (ORM) |
| **Consumed By** | `app.application` services, `app.api` routes via dependency injection |
| **SOLID Principles** | Dependency Inversion (abstractions), Single Responsibility |
| **Async Support** | Full async/await with SQLAlchemy `AsyncSession` |
