# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FedRec Dashboard is a Final Year Project (FYP) implementing a federated learning book recommender system. The project compares centralized matrix factorization (baseline) against federated learning approaches using the Goodreads dataset.

**Stack**: Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL,  Pytorch Lightning(matrix factorization), Flower framework (federated learning simulation wrapper to the lightning module)

**Package Manager**: `uv` (fast Python package manager)

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Running the Application
```bash
# Start FastAPI server (development)
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Run directly
uv run python -m app.api.main
```

### Database Migrations
```bash
# Create new migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Check current migration version
uv run alembic current
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_experiments.py

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Code Quality
```bash
# Format code
uv run black app tests

# Sort imports
uv run isort app tests

# Lint with ruff
uv run ruff check app tests

# Type checking
uv run mypy app
```

## Architecture Overview

### Clean Architecture Layers

The codebase follows clean architecture with strict separation of concerns:

```
app/
├── core/              # Domain layer (entities, business rules, interfaces)
├── application/       # Use cases and orchestration
├── infrastructure/    # External concerns (database, persistence)
├── api/              # Presentation layer (FastAPI routes, schemas)
└── utils/            # Cross-cutting concerns (logging, exceptions)
```

**Dependency Rule**: Inner layers (core) know nothing about outer layers (infrastructure, api). Dependencies point inward.

### Core Domain (app/core/)

- **experiments.py**: Domain entities `CentralizedExperiment` and `FederatedExperiment` with state machine (PENDING → RUNNING → COMPLETED/FAILED)
- **entities.py**: Data entities (`Dataset`, `LocalUserData`, `Rating`)
- **configuration.py**: Experiment hyperparameters (learning rate, regularization, n_factors)
- **metrics.py**: `ExperimentMetrics` and `PerformanceMetric` domain models
- **repositories/interfaces.py**: Repository interfaces (dependency inversion)
- **models/recommender.py**: Matrix factorization model interface

### Application Layer (app/application/)

Orchestrates domain objects and implements use cases:

- **experiment_manager.py**: Main orchestrator for running centralized/federated experiments
- **training/centralized_trainer.py**: Centralized training using scikit-surprise
- **training/federated_simulation_manager.py**: Federated training using Flower simulation
- **data/data_handler.py**: Dataset loading and preprocessing
- **reporting/metrics_calculator.py**: RMSE/MAE computation
- **reporting/metrics_logger.py**: Per-epoch/round metrics capture
- **services/**: Application services that coordinate between layers

### Infrastructure Layer (app/infrastructure/)

Adapters to external systems:

- **database.py**: SQLAlchemy async engine, session factory, `get_session()` dependency
- **models.py**: SQLAlchemy ORM models (map to database tables)
- **repositories/**: Concrete repository implementations
  - `experiment_repository.py`: Persist/retrieve experiments
  - `metrics_repository.py`: Persist training metrics
  - `base_repository.py`: Abstract base with CRUD interface

### API Layer (app/api/)

FastAPI presentation:

- **main.py**: Application entry point, CORS, exception handlers, router registration
- **routes/**: REST endpoints
  - `experiments.py`: POST /experiments, GET /experiments/{id}
  - `metrics.py`: GET /metrics/{experiment_id}
  - `health.py`: GET /health
- **schemas/**: Pydantic models for request/response validation
- **dependencies.py**: FastAPI dependency injection setup

## Key Architectural Patterns

### Repository Pattern
All data access goes through repositories. Domain layer defines interfaces (`app/core/repositories/interfaces.py`), infrastructure layer implements them (`app/infrastructure/repositories/`). This allows swapping persistence without touching business logic.

Example:
```python
# Domain defines interface
class IExperimentRepository(ABC):
    async def add(self, experiment: Experiment) -> Experiment: ...

# Infrastructure implements
class ExperimentRepository(IExperimentRepository):
    async def add(self, experiment: Experiment) -> Experiment:
        # SQLAlchemy persistence logic
```

### Domain-Driven State Machine
Experiments have strict state transitions enforced in domain entities:
- `mark_running()`: PENDING → RUNNING
- `mark_completed(metrics)`: RUNNING → COMPLETED
- `mark_failed()`: RUNNING → FAILED

Business rules live in domain entities, not in services or repositories.

### Async All The Way
SQLAlchemy uses async/await throughout (`AsyncSession`, `asyncpg`). All repository methods are `async`. FastAPI endpoints are async. Tests use `pytest-asyncio`.

## Database Schema

**Experiments Table**: Stores experiment metadata and final metrics
- `experiment_id` (UUID, PK)
- `name`, `experiment_type` (centralized/federated)
- `status` (pending/running/completed/failed)
- `config` (JSON blob with hyperparameters)
- `metrics` (JSON blob with final RMSE/MAE)

**Metrics Table**: Stores per-epoch/round training metrics for visualization
- `metric_id` (UUID, PK)
- `experiment_id` (FK)
- `epoch_or_round` (int)
- `metric_name` (rmse/mae/loss)
- `metric_value` (float)

Migrations managed by Alembic (see `alembic/` directory).

## Federated Learning Implementation

Uses Flower framework for simulation:
- **Partitioning**: `app/federated/partitioner.py` - IID user-based partitioning (each client gets exclusive set of users)
- **Strategy**: `app/federated/strategy.py` - `FedAvgItemsOnly` aggregates only item embeddings/biases (user embeddings stay local)
- **Client/Server**: `app/federated/client_app.py` and `server_app.py` define Flower apps

Key insight: User embeddings are client-local (privacy-preserving), only item parameters are aggregated globally.

## Data Flow

1. **Experiment Creation**: User creates experiment via POST `/experiments` with config
2. **Orchestration**: `experiment_manager.py` validates, marks RUNNING, delegates to trainer
3. **Training**: Either `centralized_trainer.py` or `federated_simulation_manager.py` trains model
4. **Metrics Capture**: `metrics_logger.py` captures per-epoch/round metrics
5. **Persistence**: Repositories save experiment + metrics to PostgreSQL
6. **Retrieval**: GET `/experiments/{id}` returns experiment with convergence timeline

## Testing Strategy

- **Unit tests** (`tests/unit/`): Test domain entities, calculators, trainers in isolation
- **Integration tests** (`tests/integration/`): Test repository persistence, API routes with test database
- **Test database**: Uses separate SQLite/PostgreSQL instance, initialized via `init_db()` in fixtures
- **Async fixtures**: Use `@pytest.fixture(scope="function")` with `pytest-asyncio`

## Common Gotchas

1. **Database URL**: Default is `postgresql+asyncpg://postgres:postgres@localhost:5432/fedrec`. Override via `DATABASE_URL` env var or in `app/infrastructure/database.py`
2. **Migrations**: After changing ORM models in `app/infrastructure/models.py`, MUST run `alembic revision --autogenerate`
3. **Async context**: Always use `async with get_session_factory()() as session:` pattern for manual session handling
4. **Domain validation**: Experiments validate on `__post_init__`. Invalid config raises `ConfigurationError` immediately
5. **State transitions**: Cannot mark experiment completed unless it's RUNNING. Enforced in domain layer.

## File Locations

- **Data**: Raw Goodreads data goes in `data/` (ignored in git)
- **Storage**: Model checkpoints/artifacts in `storage/` (ignored in git)
- **Logs**: Application logs in `logs/` (ignored in git)
- **Scripts**: Utility scripts in `scripts/` (e.g., `validate_infrastructure.py`)
- **Frontend**: React dashboard in `frontend/` (separate Next.js app)

## Related Documentation

See `README.md` in individual modules (`src/data/README.md`, `src/models/README.md`) for implementation details on the underlying ML pipeline (PyTorch Lightning, matrix factorization models).


## Code Formatting Preferences

### Function Signatures
- Use **single-line** format when there are **2 or fewer parameters**
- Use **multi-line** format (one parameter per line) when there are **3+ parameters**

Examples:
```python
# Good: 2 or fewer parameters
async def create_experiment(request: Request, service: ServiceDep):

# Good: 3+ parameters  
async def create_experiment(
    request: Request,
    service: ServiceDep,
    db: DatabaseDep,
):