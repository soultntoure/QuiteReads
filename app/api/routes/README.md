# API Routes

## Overview
FastAPI router modules that define HTTP endpoints for the FedRec Dashboard API. This module implements the presentation layer of the clean architecture, exposing REST endpoints for experiment lifecycle management, performance metrics tracking, and health monitoring.

## Purpose
- Define RESTful HTTP endpoints for experiment and metrics operations
- Handle request/response validation using Pydantic schemas
- Delegate business logic to application services via dependency injection
- Provide health check endpoint for monitoring application status

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| [experiments.py](#1-experimentspy) | Experiment lifecycle endpoints | 8 endpoints for CRUD, state transitions, filtering |
| [metrics.py](#2-metricspy) | Performance metrics endpoints | 4 endpoints for recording/retrieving training metrics |
| [health.py](#3-healthpy) | Health monitoring endpoint | Simple health check for uptime monitoring |

---

## 1. experiments.py

### Overview
Defines REST API endpoints for managing centralized and federated learning experiments. Handles experiment creation, retrieval, status transitions (PENDING → RUNNING → COMPLETED/FAILED), and deletion. Routes delegate to `ExperimentService` for business logic execution.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `router` | APIRouter instance | Prefix: `/experiments`, Tag: `experiments` |
| `ExperimentServiceDep` | Type alias for DI | `Annotated[ExperimentService, Depends(get_experiment_service)]` |
| `create_centralized_experiment()` | POST `/centralized` | Creates centralized experiment, returns 201 |
| `create_federated_experiment()` | POST `/federated` | Creates federated experiment with n_clients/n_rounds |
| `list_experiments()` | GET `/` | Lists all experiments with optional status/type filters |
| `get_experiment()` | GET `/{experiment_id}` | Retrieves single experiment by UUID |
| `start_experiment()` | POST `/{experiment_id}/start` | Transitions PENDING → RUNNING |
| `complete_experiment()` | POST `/{experiment_id}/complete` | Marks RUNNING → COMPLETED with final metrics |
| `fail_experiment()` | POST `/{experiment_id}/fail` | Marks RUNNING → FAILED |
| `delete_experiment()` | DELETE `/{experiment_id}` | Deletes experiment, returns 204 |

### Usage Examples

**Creating a centralized experiment:**
```python
# POST /experiments/centralized
{
    "name": "Baseline MF",
    "n_epochs": 50,
    "learning_rate": 0.01,
    "n_factors": 20,
    "regularization": 0.02
}
# Response: 201 Created with ExperimentResponse
```

**Listing experiments with filters:**
```python
# GET /experiments?status=COMPLETED&type=federated
# Returns all completed federated experiments

# GET /experiments?status=RUNNING
# Returns all currently running experiments
```

**Experiment lifecycle:**
```python
# 1. Create experiment (status: PENDING)
POST /experiments/centralized {...}

# 2. Start experiment (status: RUNNING)
POST /experiments/{id}/start

# 3. Complete with metrics (status: COMPLETED)
POST /experiments/{id}/complete
{
    "final_rmse": 0.8542,
    "final_mae": 0.6123,
    "training_time_seconds": 120.5
}
```

### Significance
This file implements the **REST API contract** for experiment management, serving as the primary interface between external clients (frontend dashboard, API consumers) and the application layer. It follows FastAPI conventions with:
- **Dependency injection** for services (loose coupling)
- **Pydantic schemas** for automatic validation and OpenAPI docs
- **HTTP status codes** following REST conventions (201 for creation, 204 for deletion)
- **Domain model conversion** via `from_domain()` and `to_domain()` adapters

The separation of concerns ensures that HTTP concerns (routing, status codes) stay at the API layer while business rules (state transitions, validation) remain in the domain/application layers.

---

## 2. metrics.py

### Overview
Provides REST endpoints for recording and retrieving performance metrics (RMSE, MAE, loss) during experiment training. Supports both individual metric recording and batch uploads. Enables filtering by metric name, client ID (for federated experiments), and training round number.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `router` | APIRouter instance | Prefix: `/experiments`, Tag: `metrics` |
| `MetricsServiceDep` | Type alias for DI | `Annotated[MetricsService, Depends(get_metrics_service)]` |
| `add_metric()` | POST `/{experiment_id}/metrics` | Adds single metric for epoch/round, returns 201 |
| `add_metrics_batch()` | POST `/{experiment_id}/metrics/batch` | Bulk upload multiple metrics in one request |
| `list_metrics()` | GET `/{experiment_id}/metrics` | Retrieves metrics with filters (name, client_id, round) |
| `delete_experiment_metrics()` | DELETE `/{experiment_id}/metrics` | Deletes all metrics for experiment, returns 204 |

### Usage Examples

**Adding individual metric:**
```python
# POST /experiments/{experiment_id}/metrics
{
    "name": "rmse",
    "value": 0.8542,
    "round_number": 10,
    "client_id": null  # null for centralized, client UUID for federated
}
# Response: 201 Created with MetricResponse
```

**Batch metric upload:**
```python
# POST /experiments/{experiment_id}/metrics/batch
{
    "metrics": [
        {"name": "rmse", "value": 0.85, "round_number": 1},
        {"name": "mae", "value": 0.62, "round_number": 1},
        {"name": "loss", "value": 1.234, "round_number": 1}
    ]
}
# Response: 201 Created with list of MetricResponse
```

**Filtering metrics:**
```python
# Get all RMSE values
GET /experiments/{id}/metrics?name=rmse

# Get metrics for specific client (federated)
GET /experiments/{id}/metrics?client_id=abc-123

# Get metrics for specific round
GET /experiments/{id}/metrics?round_number=10

# Combine filters (client + round + name)
GET /experiments/{id}/metrics?client_id=abc&round_number=5&name=rmse
```

### Significance
This module enables **real-time training progress visualization** by capturing per-epoch/round metrics. Key architectural features:
- **Batch operations** minimize HTTP overhead during training (single request for multiple metrics)
- **Flexible filtering** supports different visualization needs (convergence plots, per-client analysis)
- **Domain object construction** converts Pydantic requests to `PerformanceMetric` domain entities
- **Separation of concerns** delegates metric persistence to `MetricsService` and repository layer

The metrics endpoints are critical for the dashboard's convergence plots and performance analysis features.

---

## 3. health.py

### Overview
Simple health check endpoint for monitoring application availability and uptime. Used by load balancers, orchestration systems (Kubernetes), and monitoring tools to verify the API is responsive.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `router` | APIRouter instance | No prefix, no tags |
| `health_check()` | GET `/health` | Returns `{"status": "healthy"}` |

### Usage Examples

**Health check:**
```python
# GET /health
# Response: 200 OK
{
    "status": "healthy"
}
```

**Typical usage in infrastructure:**
```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Significance
Provides a **lightweight health check** endpoint following microservices best practices. The endpoint:
- **Requires no authentication** (publicly accessible for monitoring)
- **Has minimal overhead** (no database queries, no business logic)
- **Returns quickly** (synchronous function, not async)
- **Follows standard conventions** (200 OK indicates healthy)

In production, this endpoint is typically used by:
- Load balancers (AWS ALB, nginx) for health checks
- Container orchestration (Kubernetes liveness/readiness probes)
- Monitoring systems (Prometheus, Datadog) for uptime tracking

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Presentation layer (outermost layer in clean architecture) |
| **Dependencies** | Depends on application services (`ExperimentService`, `MetricsService`) and Pydantic schemas |
| **Dependency Direction** | Inward (follows dependency rule - depends on inner layers, not infrastructure) |
| **Testing Strategy** | Integration tests with test database, validates HTTP contracts and status codes |
| **Framework Integration** | FastAPI routers registered in `app/api/main.py` via `app.include_router()` |
| **API Documentation** | Auto-generates OpenAPI/Swagger docs via FastAPI introspection |
| **Consumed By** | Frontend dashboard (React/Next.js), API clients, monitoring systems |
| **Design Patterns** | Dependency injection, adapter pattern (domain ↔ Pydantic conversion), repository pattern (via services) |
| **SOLID Adherence** | Single Responsibility (each router handles one resource), Dependency Inversion (depends on service abstractions) |
