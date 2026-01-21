# API Schemas Module

## Overview

This module contains Pydantic models that define the API contract for the FedRec Dashboard. These schemas handle request validation, response serialization, and OpenAPI documentation generation for both centralized and federated machine learning experiments.

## Purpose

- **Request Validation**: Enforce data constraints at the API boundary before reaching business logic
- **Response Serialization**: Convert domain entities to JSON-serializable formats
- **API Documentation**: Generate OpenAPI/Swagger schemas with examples
- **Layer Decoupling**: Isolate API layer from domain layer through mapping methods

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `experiment_schemas.py` | Experiment CRUD operations | Enums, configuration, request/response models for experiments |
| `metrics_schemas.py` | Training metrics tracking | Per-round metrics, convergence analysis, client comparisons |

---

## 1. experiment_schemas.py

### Overview

Defines Pydantic models for experiment lifecycle management including creation requests for both centralized and federated experiments, and unified response schemas.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ExperimentType` | Enum for experiment paradigm | `centralized`, `federated`; has `to_domain_value()` |
| `ExperimentStatus` | Enum for state machine states | `pending`, `running`, `completed`, `failed`; has `to_domain()` |
| `AggregationStrategy` | Enum for FL aggregation | Currently `fedavg`; bidirectional domain mapping |
| `ConfigurationSchema` | Shared training hyperparameters | `learning_rate`, `batch_size`, `epochs`, `model_type` |
| `CreateCentralizedExperimentRequest` | Create centralized experiment | `name` + `config`; `to_domain_config()` adds defaults |
| `CreateFederatedExperimentRequest` | Create federated experiment | Adds `n_clients`, `n_rounds`, `aggregation_strategy` |
| `CompleteExperimentRequest` | Mark experiment complete | `final_rmse`, `final_mae`, `training_time_seconds` |
| `ExperimentMetricsSchema` | Final metrics (response) | Optional fields for incomplete experiments |
| `ExperimentResponse` | Unified experiment response | Handles both types; `from_domain()` factory |
| `ExperimentListResponse` | Paginated experiment list | `count` + `experiments` array |

### Usage Examples

**Creating a centralized experiment:**
```python
from app.api.schemas.experiment_schemas import CreateCentralizedExperimentRequest

request = CreateCentralizedExperimentRequest(
    name="Baseline MF Experiment",
    config={
        "learning_rate": 0.01,
        "batch_size": 32,
        "epochs": 10,
        "model_type": "biased_svd"
    }
)

# Convert to domain configuration
domain_config = request.to_domain_config()
```

**Creating a federated experiment:**
```python
from app.api.schemas.experiment_schemas import (
    CreateFederatedExperimentRequest,
    AggregationStrategy
)

request = CreateFederatedExperimentRequest(
    name="FedAvg Experiment",
    config={
        "learning_rate": 0.01,
        "batch_size": 32,
        "epochs": 5,
        "model_type": "biased_svd"
    },
    n_clients=10,
    n_rounds=20,
    aggregation_strategy=AggregationStrategy.FEDAVG
)
```

**Converting domain entity to response:**
```python
from app.api.schemas.experiment_schemas import ExperimentResponse

# In route handler
response = ExperimentResponse.from_domain(experiment_entity)
return response
```

### Significance

- **Type Safety**: Pydantic enforces constraints (`gt=0`, `ge=0`, `le=1`, `min_length`) at API boundary
- **Polymorphism**: Single `ExperimentResponse` handles both experiment types via `from_domain()` factory
- **Domain Isolation**: `to_domain_*` methods encapsulate conversion logic, keeping routes clean
- **OpenAPI Integration**: `json_schema_extra` provides Swagger UI examples for API consumers

---

## 2. metrics_schemas.py

### Overview

Defines Pydantic models for granular training metrics collection and analysis. Supports both centralized (epoch-based) and federated (round/client-based) metrics with analytics for convergence visualization and client comparison.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `AddMetricRequest` | Single metric submission | `name`, `value`, optional `round_number`, `client_id` |
| `AddMetricsBatchRequest` | Batch metric submission | List of `AddMetricRequest` for efficiency |
| `MetricResponse` | Single metric response | Uses `from_attributes=True` for dataclass support |
| `MetricListResponse` | Paginated metrics list | `count` + `metrics` array |
| `MetricStatisticsResponse` | Aggregate statistics | `min`, `max`, `avg` for a metric type |
| `RoundConvergenceData` | Per-round aggregates | `avg_loss`, `min_loss`, `max_loss`, `num_clients_reported` |
| `ConvergenceAnalysisResponse` | Full convergence timeline | `rounds_data` array + `convergence_trend` |
| `ClientPerformanceData` | Individual client stats | `avg`, `best`, `latest` metric values per client |
| `ClientComparisonResponse` | Cross-client comparison | Identifies best/worst performing clients |

### Usage Examples

**Submitting a single metric:**
```python
from app.api.schemas.metrics_schemas import AddMetricRequest

metric = AddMetricRequest(
    name="rmse",
    value=0.842,
    round_number=5,
    client_id="client_2"
)
```

**Batch metric submission:**
```python
from app.api.schemas.metrics_schemas import AddMetricsBatchRequest, AddMetricRequest

batch = AddMetricsBatchRequest(
    metrics=[
        AddMetricRequest(name="rmse", value=0.842, round_number=5, client_id="client_1"),
        AddMetricRequest(name="mae", value=0.656, round_number=5, client_id="client_1"),
    ]
)
```

**Building convergence analysis response:**
```python
from app.api.schemas.metrics_schemas import (
    ConvergenceAnalysisResponse,
    RoundConvergenceData
)

response = ConvergenceAnalysisResponse(
    experiment_id="550e8400-e29b-41d4-a716-446655440000",
    metric_name="rmse",
    total_rounds=20,
    rounds_data=[
        RoundConvergenceData(
            round_number=1,
            avg_loss=1.376,
            min_loss=1.234,
            max_loss=1.523,
            num_clients_reported=10
        ),
        # ... more rounds
    ],
    convergence_trend="decreasing"
)
```

### Significance

- **Federated Support**: `round_number` and `client_id` fields enable FL-specific tracking
- **Visualization Ready**: Structures map directly to frontend chart components
- **Debugging Aid**: Client comparison identifies stragglers or anomalous participants
- **Batch Efficiency**: `AddMetricsBatchRequest` reduces API calls during training

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **API Contract** | Defines the public interface consumed by the frontend dashboard |
| **Validation Boundary** | All input validation happens here before reaching domain/business logic |
| **Documentation Source** | OpenAPI schemas auto-generated from these models power Swagger UI |
| **Layer Separation** | Clean boundary between HTTP concerns and domain logic via mapping methods |
| **Type Consistency** | Shared enums ensure API and domain layers use consistent values |
