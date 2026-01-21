# Infrastructure

## Overview

The infrastructure layer provides adapters to external systems, primarily the PostgreSQL database. It implements the Repository Pattern and contains SQLAlchemy ORM models, database connection management, and concrete repository implementations.

## Purpose

- Manage async PostgreSQL connections via SQLAlchemy 2.0
- Define ORM models mapping domain entities to database tables
- Provide repository implementations for data persistence
- Isolate all database concerns from domain and application layers

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `database.py` | Connection management | Async engine, session factory, FastAPI dependency |
| `models.py` | ORM models | `ExperimentModel`, `MetricModel` table definitions |
| `repositories/` | Data access layer | Repository Pattern implementations. See [repositories/README.md](repositories/README.md) for details |

---

## Python Files in This Module

### 1. database.py

#### Overview

Provides async PostgreSQL connection management using SQLAlchemy 2.0's async API. Implements lazy initialization of engine and session factory with proper connection pooling.

#### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `DATABASE_URL` | Default connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/fedrec` |
| `Base` | Declarative base class | All ORM models inherit from this |
| `get_engine` | Engine factory | Lazy singleton with `pool_pre_ping=True` |
| `get_session_factory` | Session factory | Returns `async_sessionmaker[AsyncSession]` |
| `get_session` | FastAPI dependency | Yields session with auto commit/rollback |
| `init_db` | Table creation | Testing only - bypasses Alembic |
| `close_db` | Connection cleanup | Disposes engine and resets globals |

#### Usage Examples

```python
from app.infrastructure import get_session, init_db

# As FastAPI dependency
@app.get("/experiments")
async def list_experiments(session: AsyncSession = Depends(get_session)):
    repo = ExperimentRepository(session)
    return await repo.get_all()

# Manual session handling
from app.infrastructure.database import get_session_factory

async def manual_example():
    factory = get_session_factory()
    async with factory() as session:
        repo = ExperimentRepository(session)
        experiment = await repo.get_by_id("abc-123")

# Testing setup
async def setup_test_db():
    await init_db("sqlite+aiosqlite:///:memory:")
```

#### Significance

This module implements the **Unit of Work pattern** via SQLAlchemy sessions. The `get_session` dependency:
- Automatically commits on success
- Rolls back on exception
- Properly closes the session

---

### 2. models.py

#### Overview

Defines SQLAlchemy ORM models that map domain entities to PostgreSQL tables. Handles polymorphic experiment types and the one-to-many relationship between experiments and metrics.

#### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ExperimentModel` | Experiments table | Stores centralized and federated experiments |
| `MetricModel` | Metrics table | Per-epoch/round performance metrics |

#### ExperimentModel Fields

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `String(36)` | UUID primary key |
| `name` | `String(100)` | Experiment name |
| `experiment_type` | `String(20)` | Discriminator: "centralized" or "federated" |
| `status` | `Enum(ExperimentStatus)` | PENDING, RUNNING, COMPLETED, FAILED |
| `created_at` | `DateTime` | Creation timestamp |
| `completed_at` | `DateTime` | Completion timestamp (nullable) |
| `config` | `JSON` | Hyperparameters (n_factors, learning_rate, etc.) |
| `final_rmse` | `Float` | Final RMSE metric (nullable) |
| `final_mae` | `Float` | Final MAE metric (nullable) |
| `training_time_seconds` | `Float` | Total training duration (nullable) |
| `n_clients` | `Integer` | Federated: number of clients (nullable) |
| `n_rounds` | `Integer` | Federated: number of rounds (nullable) |
| `aggregation_strategy` | `Enum(AggregationStrategy)` | Federated: FEDAVG, etc. (nullable) |
| `metrics` | `relationship` | One-to-many with MetricModel |

#### MetricModel Fields

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `Integer` | Auto-increment primary key |
| `experiment_id` | `String(36)` | Foreign key to experiments |
| `name` | `String(50)` | Metric name: "rmse", "mae", "loss" |
| `value` | `Float` | Metric value |
| `context` | `String(50)` | Context: "global", "client", "train", "val" |
| `round_number` | `Integer` | Epoch or communication round (nullable) |
| `client_id` | `String(50)` | Federated client identifier (nullable) |
| `recorded_at` | `DateTime` | Timestamp for ordering |

#### Usage Examples

```python
from app.infrastructure.models import ExperimentModel, MetricModel

# Direct model creation (usually done via repository)
experiment = ExperimentModel(
    id="abc-123",
    name="Test Experiment",
    experiment_type="centralized",
    status=ExperimentStatus.PENDING,
    config={"n_factors": 50, "learning_rate": 0.01},
)

# Adding metrics to experiment
metric = MetricModel(
    name="rmse",
    value=0.85,
    context="train",
    round_number=1,
)
experiment.metrics.append(metric)
```

#### Significance

The models implement a **single-table inheritance** strategy for experiments:
- Both centralized and federated experiments share one table
- `experiment_type` column discriminates between types
- Federated-specific columns are nullable for centralized experiments
- Cascade delete ensures metrics are removed with experiments

---

## Subdirectories

### repositories/

**Purpose**: Concrete implementations of the Repository Pattern for data access.

**Key Components**:
- `BaseRepository` - Abstract generic interface
- `ExperimentRepository` - Experiment CRUD + queries
- `MetricsRepository` - Metrics CRUD + analytics

For technical details, see [repositories/README.md](repositories/README.md)

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Infrastructure (Adapters) |
| **Clean Architecture Role** | External interface adapter |
| **Dependencies** | `sqlalchemy`, `asyncpg`, `app.utils.types` |
| **Consumed By** | `app.application` services, `app.api` routes |
| **SOLID Principles** | Dependency Inversion (repositories implement interfaces) |
| **Patterns** | Repository, Unit of Work, Single Table Inheritance |
