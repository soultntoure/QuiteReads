# Application Services

## Overview

The application services layer implements business logic and orchestrates operations between the API and repository layers. These services coordinate experiment lifecycle management, metrics tracking, and data validation while enforcing business rules and state transitions.

## Purpose

- Orchestrate complex workflows involving multiple domain entities
- Enforce business rules and validate state transitions
- Coordinate between domain entities and repository interfaces
- Provide transaction boundaries for atomic operations
- Implement application-specific use cases

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ExperimentService` | Manages experiment lifecycle and CRUD operations | Handles creation, state transitions (PENDING→RUNNING→COMPLETED/FAILED), retrieval, and deletion |
| `MetricsService` | Manages performance metrics and analytics | Handles metric persistence, querying, aggregation, and convergence analysis |

---

## 1. experiment_service.py

### Overview

Implements the application service for managing experiment entities (centralized and federated). Coordinates between the API layer and repository layer, enforcing experiment state machine transitions and lifecycle rules.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ExperimentService` | Orchestrates experiment operations | Manages two repositories (experiments, metrics) |
| `create_centralized_experiment()` | Creates centralized experiments | Generates UUID, sets PENDING status, persists to repository |
| `create_federated_experiment()` | Creates federated experiments | Includes n_clients, n_rounds, aggregation_strategy parameters |
| `get_experiment_by_id()` | Retrieves experiment by UUID | Raises `EntityNotFoundError` if not found |
| `get_all_experiments()` | Retrieves all experiments | Returns list of all experiments regardless of status |
| `get_experiments_by_status()` | Filters experiments by status | Accepts `ExperimentStatus` enum (PENDING/RUNNING/COMPLETED/FAILED) |
| `get_experiments_by_type()` | Filters experiments by type | Accepts "centralized" or "federated" string |
| `get_experiments_by_status_and_type()` | Filters by both status and type | Combines both filtering strategies |
| `start_experiment()` | Transitions experiment to RUNNING | Validates status is PENDING before transition |
| `complete_experiment()` | Transitions to COMPLETED with metrics | Requires RUNNING status, accepts final_rmse, final_mae, training_time |
| `fail_experiment()` | Transitions to FAILED | Validates status is RUNNING before marking as failed |
| `delete_experiment()` | Deletes experiment and metrics | Cascades deletion to associated metrics |
| `experiment_exists()` | Checks experiment existence | Returns boolean without raising exceptions |

### Usage Examples

```python
from app.application.services import ExperimentService
from app.core.configuration import Configuration
from app.core.repositories import IExperimentRepository, IMetricsRepository
from app.utils.types import ExperimentStatus

# Initialize service (typically done via dependency injection)
service = ExperimentService(
    experiment_repository=experiment_repo,
    metrics_repository=metrics_repo,
)

# Create a centralized experiment
config = Configuration(
    learning_rate=0.01,
    regularization=0.02,
    n_factors=50,
    n_epochs=100,
)

experiment = await service.create_centralized_experiment(
    name="Baseline Centralized Run",
    config=config,
)

# Create a federated experiment
fed_experiment = await service.create_federated_experiment(
    name="FedAvg 10 Clients",
    config=config,
    n_clients=10,
    n_rounds=50,
    aggregation_strategy=AggregationStrategy.FEDAVG,
)

# Manage experiment lifecycle
await service.start_experiment(experiment.experiment_id)

# After training completes...
await service.complete_experiment(
    experiment_id=experiment.experiment_id,
    final_rmse=0.8234,
    final_mae=0.6421,
    training_time_seconds=123.45,
)

# Query experiments
pending_experiments = await service.get_experiments_by_status(
    ExperimentStatus.PENDING
)

centralized_experiments = await service.get_experiments_by_type(
    "centralized"
)

# Delete experiment (cascades to metrics)
await service.delete_experiment(experiment.experiment_id)
```

### Significance

This service enforces the experiment **state machine** defined in the domain layer. Key architectural patterns:

- **Single Responsibility**: Only manages experiment entities, delegates metrics to `MetricsService`
- **Dependency Inversion**: Depends on `IExperimentRepository` and `IMetricsRepository` interfaces, not concrete implementations
- **Domain-Driven Design**: State transitions (`mark_running()`, `mark_completed()`, `mark_failed()`) are called on domain entities, not in the service
- **Transaction Coordination**: Ensures cascading deletion (deletes metrics before deleting experiment)
- **Validation Layer**: Validates business rules (e.g., cannot start an experiment that's already running)

---

## 2. metrics_service.py

### Overview

Manages performance metrics operations for experiments. Handles metric persistence, retrieval with various filters, aggregate statistics, batch operations, and analytics like convergence analysis and client performance comparison.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `MetricsService` | Orchestrates metrics operations | Manages metrics_repository and experiment_repository |
| `add_metric()` | Adds single performance metric | Validates experiment exists, creates `PerformanceMetric` entity |
| `add_metrics_batch()` | Adds multiple metrics atomically | Validates all metrics belong to same experiment |
| `get_experiment_metrics()` | Retrieves all metrics for experiment | Returns all metrics regardless of round/client |
| `get_metrics_by_name()` | Filters metrics by name | Filters by metric name (rmse, mae, loss, etc.) |
| `get_client_metrics()` | Retrieves client-specific metrics | For federated experiments, filters by client_id |
| `get_round_metrics()` | Retrieves round-specific metrics | For federated experiments, filters by round_number |
| `get_metric_statistics()` | Calculates aggregate statistics | Returns min, max, avg, count for a metric |
| `calculate_final_metrics()` | Extracts final RMSE/MAE | Gets last recorded value for each metric (by round number) |
| `delete_experiment_metrics()` | Deletes all metrics for experiment | Used in cleanup or experiment deletion |
| `get_convergence_analysis()` | Analyzes metric convergence over rounds | Returns time series of metric values ordered by round |
| `get_client_performance_comparison()` | Compares average client performance | Calculates average metric value per client |

### Usage Examples

```python
from app.application.services import MetricsService
from app.core.metrics import PerformanceMetric
from app.core.repositories import IMetricsRepository, IExperimentRepository

# Initialize service
service = MetricsService(
    metrics_repository=metrics_repo,
    experiment_repository=experiment_repo,
)

# Add a single metric
metric = await service.add_metric(
    experiment_id="exp-123",
    name="rmse",
    value=0.8234,
    context="global",
    round_number=10,
)

# Add multiple metrics in a batch (e.g., from federated training)
metrics = [
    PerformanceMetric(
        name="rmse",
        value=0.85,
        experiment_id="exp-123",
        round_number=1,
        client_id="client_0",
    ),
    PerformanceMetric(
        name="mae",
        value=0.67,
        experiment_id="exp-123",
        round_number=1,
        client_id="client_0",
    ),
]
await service.add_metrics_batch("exp-123", metrics)

# Retrieve metrics with various filters
all_metrics = await service.get_experiment_metrics("exp-123")
rmse_metrics = await service.get_metrics_by_name("exp-123", "rmse")
client_0_metrics = await service.get_client_metrics("exp-123", "client_0")
round_5_metrics = await service.get_round_metrics("exp-123", 5)

# Get aggregate statistics
stats = await service.get_metric_statistics("exp-123", "rmse")
# Returns: {'min': 0.75, 'max': 0.95, 'avg': 0.83, 'count': 50}

# Calculate final metrics before completing experiment
final_metrics = await service.calculate_final_metrics("exp-123")
# Returns: {'rmse': 0.8234, 'mae': 0.6421}

# Analyze convergence over training
convergence = await service.get_convergence_analysis("exp-123", "rmse")
# Returns: [
#   {'round_number': 1, 'value': 0.95},
#   {'round_number': 2, 'value': 0.89},
#   ...
# ]

# Compare client performance in federated learning
comparison = await service.get_client_performance_comparison("exp-123", "rmse")
# Returns: {'client_0': 0.82, 'client_1': 0.85, 'client_2': 0.81}
```

### Significance

This service provides **metrics intelligence** beyond simple CRUD operations. Key architectural patterns:

- **Analytics Layer**: Implements business logic for convergence analysis, client comparison, and final metric extraction
- **Validation**: Ensures experiment exists before allowing metric operations (prevents orphaned metrics)
- **Batch Operations**: Supports atomic batch inserts for efficiency (important for federated experiments with many clients)
- **Flexibility**: Supports both centralized (round_number only) and federated (round_number + client_id) metrics
- **Separation of Concerns**: Handles metrics operations independently from experiment lifecycle

**Use Case Examples**:
- **Convergence Analysis**: Dashboard visualization of RMSE/MAE over training rounds
- **Client Heterogeneity**: Identify underperforming clients in federated learning
- **Final Metrics**: Extract last recorded metrics before marking experiment as completed
- **Statistics**: Quick aggregate views for comparison dashboards

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Application layer - orchestrates domain entities and repositories |
| **Dependencies** | Depends on `app.core` (domain entities, interfaces), `app.utils` (exceptions, types) |
| **Consumed By** | `app.api.routes` (FastAPI endpoints), `app.application.experiment_manager` (training orchestration) |
| **Design Patterns** | Service pattern, Dependency Inversion (repository interfaces), Single Responsibility |
| **Transaction Boundaries** | Services define atomic operation boundaries (e.g., delete experiment + metrics) |
| **State Management** | Enforces experiment state machine through domain entity methods |
| **Testing Strategy** | Unit test with mocked repositories, integration test with real database |
| **SOLID Adherence** | Single Responsibility (one service per aggregate root), Open-Closed (extend via new services), Dependency Inversion (depend on interfaces) |

**Key Architectural Decisions**:

1. **Repository Coordination**: Both services coordinate multiple repositories (experiments + metrics) to maintain referential integrity
2. **Domain Delegation**: State transitions are delegated to domain entities (`experiment.mark_running()`), not implemented in services
3. **Exception Handling**: Services translate repository-level errors into application-level exceptions (`EntityNotFoundError`, `ConfigurationError`)
4. **Async All the Way**: All methods are async to support SQLAlchemy async patterns and FastAPI async endpoints
5. **No Direct Database Access**: Services never touch SQLAlchemy models directly - all persistence goes through repository interfaces
