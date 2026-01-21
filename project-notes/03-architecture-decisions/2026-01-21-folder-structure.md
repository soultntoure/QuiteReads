# Project Structure

app/
├── core/
│   ├── configuration.py - Experiment hyperparameters dataclass with validation for model settings
│   ├── entities.py - Domain entities: Rating, Book, Dataset, LocalUserData for data representation
│   ├── experiments.py - Experiment domain entities with state machine (PENDING → RUNNING → COMPLETED/FAILED)
│   ├── metrics.py - PerformanceMetric and ExperimentMetrics domain models for tracking results
│   │
│   ├── models/
│   │   └── recommender.py - Matrix factorization model interface (placeholder)
│   │
│   └── repositories/
│       └── interfaces.py - Repository interfaces (Protocols) enabling dependency inversion
│
├── application/
│   ├── experiment_manager.py - Main orchestrator for running centralized/federated experiments (placeholder)
│   │
│   ├── data/
│   │   └── data_handler.py - Dataset loading and preprocessing logic (placeholder)
│   │
│   ├── training/
│   │   ├── centralized_trainer.py - Centralized training using matrix factorization (placeholder)
│   │   └── federated_simulation_manager.py - Federated training using Flower simulation (placeholder)
│   │
│   ├── reporting/
│   │   ├── export_manager.py - Export functionality for experiment results (placeholder)
│   │   ├── metrics_calculator.py - RMSE/MAE computation utilities (placeholder)
│   │   └── metrics_logger.py - Per-epoch/round metrics capture during training (placeholder)
│   │
│   └── services/
│       ├── experiment_service.py - Business logic for experiment lifecycle: create, start, complete, fail
│       └── metrics_service.py - Business logic for metrics operations, batch recording, and analytics
│
├── infrastructure/
│   ├── database.py - SQLAlchemy async engine, session factory, and connection management
│   ├── models.py - SQLAlchemy ORM models mapping domain entities to database tables
│   │
│   └── repositories/
│       ├── base_repository.py - Abstract base class defining standard CRUD operations
│       ├── experiment_repository.py - Experiment persistence with polymorphic type handling
│       └── metrics_repository.py - Metrics persistence with specialized queries for analysis
│
├── api/
│   ├── main.py - FastAPI application entry point with CORS, exception handlers, router registration
│   ├── dependencies.py - Dependency injection setup wiring repositories to services
│   │
│   ├── routes/
│   │   ├── health.py - Health check endpoint for monitoring application status
│   │   ├── experiments.py - REST endpoints for experiment CRUD and lifecycle transitions
│   │   └── metrics.py - REST endpoints for recording and querying performance metrics
│   │
│   └── schemas/
│       ├── experiment_schemas.py - Pydantic schemas for experiment request/response validation
│       └── metrics_schemas.py - Pydantic schemas for metrics data structures and analytics
│
└── utils/
    ├── exceptions.py - Custom exception classes: ConfigurationError, RepositoryError, EntityNotFoundError
    ├── types.py - Shared enums: ExperimentStatus, AggregationStrategy, ModelType
    └── logging_config.py - Logging configuration setup (placeholder)

data/
├── raw/ - Raw Goodreads dataset files (git-ignored)
└── processed/ - Preprocessed data ready for training (git-ignored)

frontend/

tests/

scripts/

---

## Summary by Module

- **core/**: Domain layer containing entities, business rules, and repository interfaces. Inner layer that knows nothing about outer layers.

- **application/**: Use cases and orchestration layer. Contains services that coordinate between domain entities and infrastructure.

- **infrastructure/**: External concerns adapter layer. Handles database persistence, ORM models, and concrete repository implementations.

- **api/**: Presentation layer with FastAPI routes, Pydantic schemas for validation, and dependency injection setup.

- **utils/**: Cross-cutting concerns including custom exceptions, shared type definitions, and logging configuration.

- **data/**: Storage for raw and processed Goodreads dataset files. Not tracked in git.

- **frontend/**: React/Next.js dashboard application (separate from backend).

- **tests/**: Unit and integration tests using pytest-asyncio.

- **scripts/**: Utility scripts for validation and maintenance tasks.
