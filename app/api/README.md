# API Layer

## Overview
FastAPI presentation layer that exposes REST endpoints for the FedRec Dashboard. This module serves as the outermost layer in the clean architecture, handling HTTP concerns, request/response validation, and delegating business logic to the application layer via dependency injection.

## Purpose
- Provide REST API entry point for frontend and external clients
- Configure FastAPI application with middleware, routers, and exception handlers
- Wire dependency injection for services and database sessions
- Define request/response schemas with Pydantic models
- Organize API routes by resource (experiments, metrics, health)

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| [main.py](#1-mainpy) | FastAPI application entry point | CORS, exception handlers, router registration |
| [dependencies.py](#2-dependenciespy) | Dependency injection setup | Service factory functions for FastAPI DI |
| [routes/](#routesdirectory) | REST endpoint routers | Experiments, metrics, health check endpoints |
| [schemas/](#schemasdirectory) | Pydantic request/response models | API contract validation and serialization |

---

## Python Files in This Module

### 1. main.py

#### Overview
FastAPI application entry point that configures global middleware (CORS), exception handlers for domain errors, and registers all API routers. Defines the OpenAPI metadata (title, description, version) and provides a `uvicorn` runner for local development.

#### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `app` | FastAPI application instance | Title: "Federated Learning Dashboard API", Version: 1.0.0 |
| `CORSMiddleware` | Cross-Origin Resource Sharing | Allows all origins/methods/headers (development config) |
| `entity_not_found_handler()` | 404 error handler | Maps `EntityNotFoundError` → HTTP 404 JSON response |
| `configuration_error_handler()` | 422 error handler | Maps `ConfigurationError` → HTTP 422 (invalid experiment config) |
| `repository_error_handler()` | 500 error handler | Maps `RepositoryError` → HTTP 500 (database failures) |
| Router includes | Router registration | `health.router`, `experiments.router`, `metrics.router` |
| `if __name__ == "__main__"` | Development runner | Starts uvicorn on 0.0.0.0:8000 with auto-reload |

#### Usage Examples

**Running the application:**
```bash
# Development mode with auto-reload
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uv run python -m app.api.main
```

**Exception handler behavior:**
```python
# Domain layer raises EntityNotFoundError
raise EntityNotFoundError("Experiment", "abc-123")

# FastAPI converts to HTTP response:
# HTTP 404 Not Found
# {"detail": "Experiment with ID abc-123 not found"}

# Configuration validation error
raise ConfigurationError("learning_rate must be positive")

# HTTP 422 Unprocessable Entity
# {"detail": "learning_rate must be positive"}
```

**Accessing OpenAPI docs:**
```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc

# OpenAPI JSON schema
http://localhost:8000/openapi.json
```

#### Significance
This file is the **application bootstrap** that wires together all API components. Key architectural decisions:

- **Global exception handlers** convert domain exceptions to proper HTTP status codes, preventing stack traces from leaking to clients
- **CORS middleware** enables frontend dashboard (running on different port/domain) to make API requests
- **Router composition** follows separation of concerns - each router handles one resource type
- **OpenAPI integration** automatically generates interactive API documentation from route definitions and Pydantic schemas
- **Development convenience** provides `python -m app.api.main` entry point for quick testing

The centralized configuration ensures consistent error handling across all endpoints and provides a single source of truth for API metadata.

---

### 2. dependencies.py

#### Overview
Dependency injection factory functions for FastAPI routes. Wires up application services with their required repositories and database sessions. Uses FastAPI's `Depends()` mechanism to create service instances per-request with automatic cleanup.

#### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `get_experiment_service()` | ExperimentService factory | Injects `AsyncSession`, creates repositories, returns service |
| `get_metrics_service()` | MetricsService factory | Injects `AsyncSession`, creates repositories, returns service |
| Type annotations | Dependency injection hints | Uses `Annotated[AsyncSession, Depends(get_session)]` pattern |

#### Usage Examples

**Using dependencies in routes:**
```python
# In app/api/routes/experiments.py
from app.api.dependencies import get_experiment_service

# Type alias for cleaner signatures
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]

@router.post("/experiments/centralized")
async def create_centralized_experiment(
    request: CreateCentralizedExperimentRequest,
    service: ExperimentServiceDep,  # FastAPI injects this
):
    # Service already has repositories wired, database session managed
    experiment = await service.create_centralized_experiment(...)
    return experiment
```

**Dependency injection flow:**
```python
# 1. FastAPI sees ExperimentServiceDep annotation
# 2. Calls get_experiment_service()
# 3. get_experiment_service() needs AsyncSession
# 4. FastAPI calls get_session() (from infrastructure layer)
# 5. get_session() yields a database session
# 6. get_experiment_service() creates repositories with session
# 7. Returns ExperimentService instance
# 8. Route function executes with injected service
# 9. After route completes, session is automatically closed (yield cleanup)
```

**Manual dependency override (testing):**
```python
# In tests
from app.api.main import app
from app.api.dependencies import get_experiment_service

def override_experiment_service():
    # Return mock service
    return MockExperimentService()

app.dependency_overrides[get_experiment_service] = override_experiment_service
```

#### Significance
This module implements the **dependency injection pattern** that enables clean architecture principles:

- **Inversion of Control**: Routes don't create services - FastAPI injects them
- **Testability**: Easy to override dependencies with mocks in tests
- **Lifecycle management**: Database sessions are automatically created/closed per-request
- **Separation of concerns**: Routes don't know about repository or database details
- **Single Responsibility**: Each factory function constructs one service with its dependencies

The pattern ensures that:
1. Database sessions are properly scoped to request lifecycle (no connection leaks)
2. Services are created fresh per-request (no shared state bugs)
3. Dependencies flow inward (presentation → application → infrastructure)
4. Testing can inject mock services without modifying route code

This is a **key enabler of clean architecture** - outer layers (API) depend on inner layers (services) via abstractions (dependency injection).

---

## Subdirectories

### routes/

**Purpose**: FastAPI router modules that define REST endpoints for experiments, metrics, and health monitoring.

**Key Components**:
- `experiments.py` - 8 endpoints for experiment lifecycle (create, list, get, start, complete, fail, delete)
- `metrics.py` - 4 endpoints for performance metrics recording and retrieval
- `health.py` - 1 endpoint for health checks

For detailed technical documentation, see [routes/README.md](routes/README.md)

---

### schemas/

**Purpose**: Pydantic models for API request/response validation and serialization.

**Key Components**:
- `experiment_schemas.py` - Request/response models for experiments
- `metrics_schemas.py` - Request/response models for performance metrics
- Domain-to-Pydantic conversion with `from_domain()` and `to_domain()` adapters

For detailed technical documentation, see [schemas/README.md](schemas/README.md)

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Presentation layer (outermost layer in clean architecture) |
| **Dependencies** | Depends on `app.application` (services), `app.infrastructure` (database, repositories), `app.core` (domain entities) |
| **Dependency Direction** | Inward (follows dependency rule - outer layers depend on inner layers) |
| **Consumed By** | Frontend dashboard (React/Next.js), API clients, monitoring tools |
| **Testing Strategy** | Integration tests with test database, validates HTTP contracts, status codes, and JSON responses |
| **Framework** | FastAPI 0.100+ with async/await, automatic OpenAPI generation, dependency injection |
| **Design Patterns** | Dependency Injection (services), Adapter Pattern (Pydantic ↔ domain), Repository Pattern (via services), Exception Mapping (domain → HTTP) |
| **SOLID Adherence** | Single Responsibility (each file has one concern), Dependency Inversion (depends on service abstractions), Interface Segregation (focused router interfaces) |
| **API Documentation** | Auto-generated OpenAPI/Swagger docs at `/docs` and `/redoc` |
| **Error Handling** | Domain exceptions mapped to HTTP status codes (404, 422, 500) with JSON error responses |
| **CORS Configuration** | Permissive (allow all) - should be restricted in production to frontend domain only |
| **Entry Point** | `uvicorn app.api.main:app --reload` for development, `python -m app.api.main` for direct execution |
