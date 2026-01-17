# API Layer (app/api)

## Overview

The API layer is the presentation tier in the FedRec Dashboard's clean architecture, built with FastAPI. It exposes the experiment management and metrics tracking functionality through RESTful HTTP endpoints, serving as the single entry point for all external client requests (including the React frontend).

This module defines the HTTP interface, request/response validation schemas, dependency injection setup, and global exception handling. All business logic is orchestrated through the application layer services, which in turn leverage domain and infrastructure layers.

## Purpose

The API layer exists to:

1. **Expose business capabilities as HTTP endpoints** - Transform application layer use cases into REST resources
2. **Validate all inputs** - Use Pydantic schemas to enforce data contracts before domain logic processes requests
3. **Translate domain exceptions to HTTP responses** - Map internal errors to appropriate HTTP status codes
4. **Enable cross-origin requests** - Configure CORS for frontend integration
5. **Inject dependencies** - Wire repositories, services, and database sessions into route handlers

## Architecture Pattern

The API layer follows **dependency injection** and **layered architecture** patterns:

```
Client Request
    ↓
FastAPI Route Handler (app/api/routes/*)
    ↓
Pydantic Schema Validation (app/api/schemas/*)
    ↓
Application Service (app/application/services/*)
    ↓
Domain Layer (app/core/*)
    ↓
Infrastructure Layer (app/infrastructure/*)
    ↓
Database
```

Each route depends on an application service (injected via `Depends()`), which orchestrates domain logic and interacts with repositories. The API layer never directly accesses repositories or domain objects—it delegates to services.

---

## File-by-File Documentation

### main.py

**Location**: `app/api/main.py`

Entry point for the FastAPI application. Configures the app instance, middleware, global exception handlers, and registers all route routers.

**Components**:

| Component | Type | Description |
|-----------|------|-------------|
| `app` | FastAPI instance | Main application object with title "Federated Learning Dashboard API", version 1.0.0 |
| `CORSMiddleware` | Middleware | Allows requests from any origin with all methods and headers (permissive for development) |
| `@app.exception_handler(EntityNotFoundError)` | Exception handler | Returns 404 JSON response when an entity is not found |
| `@app.exception_handler(ConfigurationError)` | Exception handler | Returns 422 (Unprocessable Entity) JSON response for invalid configurations |
| `@app.exception_handler(RepositoryError)` | Exception handler | Returns 500 (Internal Server Error) JSON response for data access failures |

**Key Details**:

- Imports and registers routers from `health`, `experiments`, and `metrics` route modules
- Exception handlers catch domain-layer exceptions and convert them to appropriate HTTP responses
- CORS middleware is configured permissively (`allow_origins=["*"]`), suitable for development but should be restricted in production
- Includes `__main__` block for standalone execution via `uvicorn.run()`

**Usage**:

```bash
# Start development server (with auto-reload)
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Start production server
uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

---

### dependencies.py

**Location**: `app/api/dependencies.py`

Implements FastAPI dependency injection functions. Dependencies are used in route handlers via `Depends()` to automatically construct service instances with wired repositories.

**Components**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_experiment_service()` | `async (db: AsyncSession) -> ExperimentService` | Creates and returns an `ExperimentService` instance with `ExperimentRepository` and `MetricsRepository` initialized from the database session. Used in experiment route handlers. |
| `get_metrics_service()` | `async (db: AsyncSession) -> MetricsService` | Creates and returns a `MetricsService` instance with `MetricsRepository` and `ExperimentRepository` initialized from the database session. Used in metrics route handlers. |

**Key Details**:

- Dependencies receive `AsyncSession` automatically from FastAPI (via the global `get_session` dependency already configured in `app/infrastructure/database.py`)
- Both functions are async and marked as FastAPI dependencies
- Each creates fresh repository instances per request (no caching)
- Repositories are passed by constructor injection to services

**Example Usage in Routes**:

```python
@router.get("/experiments/{id}")
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),  # FastAPI injects session
):
    service = await get_experiment_service(db)  # Dependency function constructs service
    experiment = await service.get_experiment_by_id(experiment_id)
    return ExperimentResponse.from_orm(experiment)
```

---

### routes/experiments.py

**Location**: `app/api/routes/experiments.py`

Defines REST endpoints for experiment lifecycle management (create, list, retrieve, start, complete, fail, delete).

**Router Configuration**:
- Prefix: `/experiments`
- Tag: `experiments` (for OpenAPI documentation)

**Endpoints**:

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/experiments/centralized` | 201 | Create a new centralized learning experiment |
| POST | `/experiments/federated` | 201 | Create a new federated learning experiment |
| GET | `/experiments` | 200 | List all experiments with optional status/type filters |
| GET | `/experiments/{experiment_id}` | 200 | Retrieve a single experiment by ID |
| POST | `/experiments/{experiment_id}/start` | 200 | Transition experiment to RUNNING state |
| POST | `/experiments/{experiment_id}/complete` | 200 | Transition experiment to COMPLETED with final metrics |
| POST | `/experiments/{experiment_id}/fail` | 200 | Transition experiment to FAILED state |
| DELETE | `/experiments/{experiment_id}` | 204 | Delete an experiment and its metrics |

**Route Functions**:

#### `create_centralized_experiment(request, db)`
Creates a new centralized (non-federated) experiment.

**Request Body** (`CreateCentralizedExperimentRequest`):
```json
{
  "name": "Centralized Baseline Exp 1",
  "config": {
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 10,
    "model_type": "matrix_factorization"
  }
}
```

**Response** (201): `ExperimentResponse` with experiment metadata and status PENDING

**Errors**:
- 422: ConfigurationError if config is invalid

---

#### `create_federated_experiment(request, db)`
Creates a new federated learning experiment.

**Request Body** (`CreateFederatedExperimentRequest`):
```json
{
  "name": "Federated Learning Exp 1",
  "config": {
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 5,
    "model_type": "matrix_factorization"
  },
  "n_clients": 5,
  "n_rounds": 20,
  "aggregation_strategy": "FedAvg"
}
```

**Response** (201): `ExperimentResponse` with experiment metadata, status PENDING, and federated-specific fields (n_clients, n_rounds, aggregation_strategy)

**Errors**:
- 422: ConfigurationError if config or federated parameters are invalid

---

#### `list_experiments(status_filter, type_filter, db)`
Lists experiments with optional filtering.

**Query Parameters**:
- `status_filter` (optional): Filter by status (pending, running, completed, failed)
- `type_filter` (optional): Filter by type (centralized, federated)

**Request**: `GET /experiments?status_filter=running&type_filter=federated`

**Response** (200): `ExperimentListResponse`
```json
{
  "count": 2,
  "experiments": [
    { "id": 1, "name": "...", "type": "federated", "status": "running", ... },
    { "id": 2, "name": "...", "type": "federated", "status": "running", ... }
  ]
}
```

---

#### `get_experiment(experiment_id, db)`
Retrieves a single experiment by UUID.

**Request**: `GET /experiments/{experiment_id}`

**Response** (200): `ExperimentResponse` - Full experiment metadata and current state

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

#### `start_experiment(experiment_id, db)`
Transitions an experiment from PENDING to RUNNING state.

**Request**: `POST /experiments/{experiment_id}/start`

**Response** (200): `ExperimentResponse` with status updated to RUNNING

**Errors**:
- 404: EntityNotFoundError if experiment does not exist
- 400: ConfigurationError if experiment is not in PENDING state

---

#### `complete_experiment(experiment_id, request, db)`
Transitions an experiment from RUNNING to COMPLETED with final metrics.

**Request Body** (`CompleteExperimentRequest`):
```json
{
  "final_rmse": 0.45,
  "final_mae": 0.32,
  "training_time_seconds": 3600.5
}
```

**Response** (200): `ExperimentResponse` with status COMPLETED and metrics populated

**Errors**:
- 404: EntityNotFoundError if experiment does not exist
- 400: ConfigurationError if experiment is not in RUNNING state

---

#### `fail_experiment(experiment_id, db)`
Transitions an experiment from RUNNING to FAILED state.

**Request**: `POST /experiments/{experiment_id}/fail`

**Response** (200): `ExperimentResponse` with status updated to FAILED

**Errors**:
- 404: EntityNotFoundError if experiment does not exist
- 400: ConfigurationError if experiment is not in RUNNING state

---

#### `delete_experiment(experiment_id, db)`
Deletes an experiment and all associated metrics.

**Request**: `DELETE /experiments/{experiment_id}`

**Response** (204): No content

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

### routes/metrics.py

**Location**: `app/api/routes/metrics.py`

Defines endpoints for recording and retrieving experiment performance metrics (loss, RMSE, MAE per epoch/round).

**Router Configuration**:
- Prefix: `/experiments` (metrics are nested under experiments)
- Tag: `metrics` (for OpenAPI documentation)

**Endpoints**:

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/experiments/{experiment_id}/metrics` | 201 | Record a single metric for an experiment |
| POST | `/experiments/{experiment_id}/metrics/batch` | 201 | Record multiple metrics in one request |
| GET | `/experiments/{experiment_id}/metrics` | 200 | List metrics for an experiment |
| DELETE | `/experiments/{experiment_id}/metrics` | 204 | Delete all metrics for an experiment |

**Route Functions**:

#### `add_metric(experiment_id, request, db)`
Records a single performance metric (e.g., loss, RMSE at epoch 5).

**Request Body** (`AddMetricRequest`):
```json
{
  "name": "rmse",
  "value": 0.87,
  "round_number": 5,
  "client_id": 2,
  "timestamp": "2025-12-19T14:30:00"
}
```

**Response** (201): `MetricResponse` with recorded metric and auto-generated ID

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

#### `add_metrics_batch(experiment_id, request, db)`
Records multiple metrics in a single request (efficient for bulk logging).

**Request Body** (`AddMetricsBatchRequest`):
```json
{
  "metrics": [
    { "name": "rmse", "value": 0.87, "round_number": 5, "client_id": 0 },
    { "name": "rmse", "value": 0.84, "round_number": 5, "client_id": 1 },
    { "name": "rmse", "value": 0.89, "round_number": 5, "client_id": 2 },
    { "name": "loss", "value": 2.3, "round_number": 5, "client_id": null }
  ]
}
```

**Response** (201): Array of `MetricResponse` objects

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

#### `list_metrics(experiment_id, name, client_id, round_number, db)`
Lists metrics for an experiment with optional filtering.

**Query Parameters**:
- `name` (optional): Filter by metric name (e.g., "rmse", "mae", "loss")
- `client_id` (optional): Filter by client (federated experiments)
- `round_number` (optional): Filter by round/epoch number

**Request**: `GET /experiments/{experiment_id}/metrics?name=rmse&round_number=5`

**Response** (200): `MetricListResponse`
```json
{
  "count": 3,
  "metrics": [
    { "id": 1, "experiment_id": 123, "name": "rmse", "value": 0.87, "round_number": 5, "client_id": 0, "timestamp": "..." },
    { "id": 2, "experiment_id": 123, "name": "rmse", "value": 0.84, "round_number": 5, "client_id": 1, "timestamp": "..." },
    { "id": 3, "experiment_id": 123, "name": "rmse", "value": 0.89, "round_number": 5, "client_id": 2, "timestamp": "..." }
  ]
}
```

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

#### `delete_experiment_metrics(experiment_id, db)`
Deletes all metrics associated with an experiment.

**Request**: `DELETE /experiments/{experiment_id}/metrics`

**Response** (204): No content

**Errors**:
- 404: EntityNotFoundError if experiment does not exist

---

### routes/health.py

**Location**: `app/api/routes/health.py`

Simple health check endpoint for monitoring application status.

**Endpoints**:

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | 200 | Health check - confirms API is running |

**Route Functions**:

#### `health_check()`
Basic health check endpoint.

**Request**: `GET /health`

**Response** (200):
```json
{
  "status": "healthy"
}
```

**Note**: This endpoint does not verify database connectivity—it only confirms the API process is running.

---

### schemas/experiment_schemas.py

**Location**: `app/api/schemas/experiment_schemas.py`

Pydantic models for experiment-related request and response validation. These schemas enforce data contracts and provide OpenAPI documentation.

**Enums**:

| Name | Values | Purpose |
|------|--------|---------|
| `ExperimentType` | CENTRALIZED, FEDERATED | Discriminates experiment flavor |
| `ExperimentStatus` | PENDING, RUNNING, COMPLETED, FAILED | Experiment state in lifecycle |
| `AggregationStrategy` | FedAvg, FedProx, FedAdam | Federated learning aggregation algorithms |

**Schemas**:

#### `ConfigurationSchema`
Shared hyperparameter configuration for both centralized and federated experiments.

**Fields**:
- `learning_rate: float` - Learning rate (0 < lr ≤ 1)
- `batch_size: int` - Batch size (> 0)
- `epochs: int` - Number of training epochs (> 0)
- `model_type: str` - Type of model ("matrix_factorization", etc.)

**Example**:
```json
{
  "learning_rate": 0.01,
  "batch_size": 32,
  "epochs": 10,
  "model_type": "matrix_factorization"
}
```

---

#### `CreateCentralizedExperimentRequest`
Request payload for creating a centralized experiment.

**Fields**:
- `name: str` - Experiment name (1-255 characters)
- `config: ConfigurationSchema` - Training hyperparameters

**Example**:
```json
{
  "name": "Centralized Baseline 1",
  "config": {
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 10,
    "model_type": "matrix_factorization"
  }
}
```

---

#### `CreateFederatedExperimentRequest`
Request payload for creating a federated experiment.

**Fields**:
- `name: str` - Experiment name (1-255 characters)
- `config: ConfigurationSchema` - Training hyperparameters
- `n_clients: int` - Number of federated clients (> 0)
- `n_rounds: int` - Number of federated rounds (> 0)
- `aggregation_strategy: AggregationStrategy` - Aggregation algorithm

**Example**:
```json
{
  "name": "Federated Learning Exp 1",
  "config": {
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 5,
    "model_type": "matrix_factorization"
  },
  "n_clients": 5,
  "n_rounds": 20,
  "aggregation_strategy": "FedAvg"
}
```

---

#### `CompleteExperimentRequest`
Request payload to mark an experiment completed with final metrics.

**Fields**:
- `final_rmse: float` - Final RMSE score (≥ 0)
- `final_mae: float` - Final MAE score (≥ 0)
- `training_time_seconds: float` - Total training duration (> 0)

**Example**:
```json
{
  "final_rmse": 0.45,
  "final_mae": 0.32,
  "training_time_seconds": 3600.5
}
```

---

#### `ExperimentMetricsSchema`
Optional final metrics for an experiment (null until completion).

**Fields**:
- `final_rmse: Optional[float]` - Final RMSE (≥ 0 or null)
- `final_mae: Optional[float]` - Final MAE (≥ 0 or null)
- `training_time_seconds: Optional[float]` - Training duration (≥ 0 or null)

---

#### `ExperimentResponse`
Unified response for both centralized and federated experiments.

**Fields**:
- `id: int` - Experiment ID
- `name: str` - Experiment name
- `type: ExperimentType` - "centralized" or "federated"
- `status: ExperimentStatus` - Current state
- `config: ConfigurationSchema` - Training config (nested)
- `metrics: ExperimentMetricsSchema` - Final metrics (nested)
- `n_clients: Optional[int]` - Number of clients (null for centralized)
- `n_rounds: Optional[int]` - Number of rounds (null for centralized)
- `aggregation_strategy: Optional[AggregationStrategy]` - Strategy (null for centralized)
- `created_at: datetime` - Creation timestamp (ISO 8601)
- `updated_at: datetime` - Last update timestamp (ISO 8601)

**Example**:
```json
{
  "id": 1,
  "name": "Federated Learning Exp 1",
  "type": "federated",
  "status": "running",
  "config": {
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 5,
    "model_type": "matrix_factorization"
  },
  "metrics": {
    "final_rmse": null,
    "final_mae": null,
    "training_time_seconds": null
  },
  "n_clients": 5,
  "n_rounds": 20,
  "aggregation_strategy": "FedAvg",
  "created_at": "2025-12-19T10:30:00",
  "updated_at": "2025-12-19T11:00:00"
}
```

---

#### `ExperimentListResponse`
Wrapper for paginated/filtered experiment lists.

**Fields**:
- `count: int` - Total experiments in list (≥ 0)
- `experiments: List[ExperimentResponse]` - Array of experiment responses

**Example**:
```json
{
  "count": 2,
  "experiments": [
    { "id": 1, "name": "...", ... },
    { "id": 2, "name": "...", ... }
  ]
}
```

---

### schemas/metrics_schemas.py

**Location**: `app/api/schemas/metrics_schemas.py`

Pydantic models for performance metric data structures used in recording and retrieval.

**Request Schemas**:

#### `AddMetricRequest`
Request to record a single metric.

**Fields**:
- `name: str` - Metric name (e.g., "rmse", "mae", "loss")
- `value: float` - Metric value
- `round_number: Optional[int]` - Training round/epoch (≥ 0)
- `client_id: Optional[int]` - Federated client ID (≥ 0)
- `timestamp: Optional[datetime]` - Metric timestamp (defaults to now)

**Example**:
```json
{
  "name": "rmse",
  "value": 0.87,
  "round_number": 5,
  "client_id": 2,
  "timestamp": "2025-12-19T14:30:00"
}
```

---

#### `AddMetricsBatchRequest`
Request to record multiple metrics at once.

**Fields**:
- `metrics: List[AddMetricRequest]` - Array of metrics (≥ 1)

**Example**:
```json
{
  "metrics": [
    { "name": "rmse", "value": 0.87, "round_number": 5, "client_id": 0 },
    { "name": "rmse", "value": 0.84, "round_number": 5, "client_id": 1 }
  ]
}
```

---

**Response Schemas**:

#### `MetricResponse`
Single metric in responses.

**Fields**:
- `id: int` - Metric ID (database-generated)
- `experiment_id: int` - Associated experiment ID
- `name: str` - Metric name
- `value: float` - Metric value
- `round_number: Optional[int]` - Round/epoch number
- `client_id: Optional[int]` - Client ID (federated)
- `timestamp: datetime` - When metric was recorded

**Example**:
```json
{
  "id": 42,
  "experiment_id": 1,
  "name": "rmse",
  "value": 0.87,
  "round_number": 5,
  "client_id": 2,
  "timestamp": "2025-12-19T14:30:00"
}
```

---

#### `MetricListResponse`
Wrapper for metric lists.

**Fields**:
- `count: int` - Number of metrics
- `metrics: List[MetricResponse]` - Array of metric responses

---

**Analysis Schemas** (for future feature extensibility):

#### `MetricStatisticsResponse`
Aggregate statistics for a metric across an experiment.

**Fields**:
- `metric_name: str` - Name of metric
- `count: int` - Total metric records
- `min_value: float` - Minimum value observed
- `max_value: float` - Maximum value observed
- `avg_value: float` - Average value
- `latest_value: Optional[float]` - Most recent value
- `latest_timestamp: Optional[datetime]` - Timestamp of latest value

---

#### `RoundConvergenceData`
Per-round convergence statistics (federated learning).

**Fields**:
- `round_number: int` - Federated round number
- `avg_loss: float` - Average loss across clients
- `min_loss: float` - Minimum loss
- `max_loss: float` - Maximum loss
- `num_clients_reported: int` - How many clients reported in round

---

#### `ConvergenceAnalysisResponse`
Convergence trend analysis for an experiment.

**Fields**:
- `experiment_id: int` - Experiment ID
- `metric_name: str` - Analyzed metric
- `total_rounds: int` - Total rounds/epochs
- `rounds_data: List[RoundConvergenceData]` - Per-round data
- `convergence_trend: str` - Trend description ("improving", "degrading", "stable")

---

#### `ClientPerformanceData`
Per-client performance metrics.

**Fields**:
- `client_id: int` - Federated client ID
- `avg_metric_value: float` - Average metric value
- `best_metric_value: float` - Best (lowest) metric value
- `latest_metric_value: Optional[float]` - Most recent value
- `num_updates: int` - Number of updates client made

---

#### `ClientComparisonResponse`
Comparison of client performance within a federated experiment.

**Fields**:
- `experiment_id: int` - Experiment ID
- `metric_name: str` - Analyzed metric
- `total_clients: int` - Number of clients
- `clients_data: List[ClientPerformanceData]` - Per-client data
- `best_performing_client_id: Optional[int]` - Best client ID
- `worst_performing_client_id: Optional[int]` - Worst client ID

---

## Layering and Interaction

### Data Flow: Request to Response

1. **FastAPI Route Handler** (e.g., `create_centralized_experiment()`)
   - Receives HTTP request
   - FastAPI automatically deserializes/validates JSON against Pydantic schema
   - If validation fails, FastAPI returns 422 with validation errors

2. **Dependency Injection** 
   - `Depends(get_session)` injects database `AsyncSession`
   - `Depends(get_experiment_service)` injects configured `ExperimentService`

3. **Service Layer** (from `app/application/services/`)
   - Orchestrates business logic
   - Calls domain layer to create experiment entities
   - Persists via repositories (from `app/infrastructure/`)
   - Returns domain entity (not response schema)

4. **Exception Handling**
   - If domain raises `ConfigurationError`, global exception handler catches it
   - Returns 422 JSON response with error detail

5. **Response Schema**
   - Route converts domain entity to response schema via `.from_orm(experiment)`
   - FastAPI serializes schema to JSON and returns HTTP response

### Dependency Mapping

| Route Dependency | Injected By | Provided By | Purpose |
|------------------|-------------|-------------|---------|
| `db: AsyncSession` | FastAPI built-in | `app/infrastructure/database.py` | Database session for repositories |
| `ExperimentService` | `get_experiment_service()` | `app/api/dependencies.py` | Orchestrates experiment operations |
| `MetricsService` | `get_metrics_service()` | `app/api/dependencies.py` | Orchestrates metrics operations |

### Service to Infrastructure Mapping

| Service | Repositories Used | Location |
|---------|-------------------|----------|
| `ExperimentService` | `ExperimentRepository`, `MetricsRepository` | `app/infrastructure/repositories/` |
| `MetricsService` | `MetricsRepository`, `ExperimentRepository` | `app/infrastructure/repositories/` |

---

## Exception Handling

The API layer converts domain-layer exceptions to HTTP responses:

| Exception | HTTP Status | Meaning | Example |
|-----------|------------|---------|---------|
| `EntityNotFoundError` | 404 | Requested experiment/metric does not exist | GET /experiments/{invalid-id} |
| `ConfigurationError` | 422 | Invalid hyperparameters or state transition | POST /experiments/centralized with invalid config |
| `RepositoryError` | 500 | Database or persistence failure | Database connection lost during save |

**Exception handling code** (in `main.py`):

```python
@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )
```

---

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Create centralized experiment
curl -X POST http://localhost:8000/experiments/centralized \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Baseline",
    "config": {
      "learning_rate": 0.01,
      "batch_size": 32,
      "epochs": 10,
      "model_type": "matrix_factorization"
    }
  }'

# List experiments
curl http://localhost:8000/experiments

# Get single experiment
curl http://localhost:8000/experiments/1

# Add metric
curl -X POST http://localhost:8000/experiments/1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rmse",
    "value": 0.87,
    "round_number": 5,
    "client_id": null
  }'

# List metrics
curl http://localhost:8000/experiments/1/metrics
```

### Using FastAPI Interactive Docs

Start the server and navigate to:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These auto-generated interfaces allow testing all endpoints with interactive forms.

---

## CORS Configuration

Currently, the API allows requests from **any origin** with all HTTP methods and headers:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins
    allow_credentials=True,         # Allow credentials (cookies, auth headers)
    allow_methods=["*"],            # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],            # Allow all headers
)
```

### Production Recommendation

For production deployment, restrict CORS to specific frontend domain(s):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

## OpenAPI Documentation

FastAPI automatically generates OpenAPI (Swagger) documentation based on:
- Route function docstrings
- Request/response schemas
- Query parameter definitions
- Status codes

**Access documentation**:
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- OpenAPI JSON: `GET /openapi.json`

All endpoints, schemas, and examples in this module's Pydantic classes appear in these auto-generated docs.

---

## Future Extensibility

The API layer is designed to accommodate future features:

1. **Authentication/Authorization**: Add JWT/OAuth2 dependency and wrap routes
2. **Pagination**: Extend list endpoints with `skip` and `limit` query parameters
3. **Pagination**: Extend list endpoints with `skip` and `limit` query parameters
4. **Caching**: Wrap service calls with Redis caching dependency
5. **Rate Limiting**: Add rate limiter middleware to prevent abuse
6. **Advanced Metrics**: Use `MetricStatisticsResponse`, `ConvergenceAnalysisResponse`, and `ClientComparisonResponse` schemas for new analysis endpoints
7. **Versioning**: Add API versioning (e.g., `/api/v1/experiments`) if breaking changes arise

---

## Significance to the Project

The API layer is critical to the FedRec Dashboard because:

1. **Frontend Integration**: The React dashboard communicates exclusively through these endpoints—without the API, the UI has no way to trigger experiments or retrieve results.

2. **Clean Architecture Enforcement**: By accepting only validated Pydantic schemas and returning domain entities via `.from_orm()`, the API enforces the separation between presentation and business logic.

3. **Error Transparency**: Global exception handlers ensure all domain-layer errors are translated to standard HTTP responses, making debugging easier for frontend developers and API consumers.

4. **Observable Behavior**: OpenAPI documentation automatically reflects the current API contract—no manual docs to maintain.

5. **Type Safety**: Pydantic schemas catch invalid requests at the boundary, preventing downstream layer bugs and reducing security surface area.

6. **Testability**: Dependency injection design allows easy mocking of services in unit tests without hitting the database.

---

## Summary Table: Quick Reference

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.12 |
| **Framework** | FastAPI |
| **Async** | Fully async (AsyncSession, async route handlers, async services) |
| **Request Validation** | Pydantic schemas with field constraints |
| **Response Validation** | Pydantic schemas with `.from_orm()` for ORM objects |
| **Database Access** | AsyncSession injected via `Depends(get_session)` |
| **Services** | ExperimentService, MetricsService injected via custom dependency functions |
| **Exceptions** | EntityNotFoundError (404), ConfigurationError (422), RepositoryError (500) |
| **CORS** | Permissive (allow_origins=["*"]) - restrict for production |
| **Documentation** | Auto-generated OpenAPI (Swagger/ReDoc) at `/docs` and `/redoc` |
| **Status Codes** | 201 (created), 200 (success), 204 (no content), 400/404/422/500 (errors) |
| **State Machine** | PENDING → RUNNING → COMPLETED/FAILED (enforced in domain layer) |

