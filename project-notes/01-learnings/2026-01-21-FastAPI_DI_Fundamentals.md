# FastAPI Dependency Injection - Complete Guide

> **Purpose**: Understand how FastAPI DI works from first principles, using real examples from the FedRec Dashboard codebase.

---

## Table of Contents

1. [What is Dependency Injection?](#1-what-is-dependency-injection)
2. [Why DI Matters](#2-why-di-matters)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Three Primitives](#4-the-three-primitives)
   - [Simple Dependencies](#41-simple-dependencies)
   - [Contextual Dependencies (yield)](#42-contextual-dependencies-yield)
   - [Nested Dependencies (composition)](#43-nested-dependencies-composition)
5. [Real Examples from FedRec](#5-real-examples-from-fedrec)
6. [Common Patterns](#6-common-patterns)
7. [Quick Reference](#7-quick-reference)

---

## 1. What is Dependency Injection?

### The One-Sentence Definition

> **Dependency Injection** = Instead of a function creating what it needs, it **receives** what it needs from the outside.

### Without DI (Bad)

```python
async def create_experiment(request: Request):
    # Function creates its own dependencies - TIGHTLY COUPLED
    session = AsyncSession(engine)
    repo = ExperimentRepository(session)
    service = ExperimentService(repo)
    return await service.create(request)
```

**Problems**:
- Hard to test (can't swap the real database for a mock)
- Hard to change (want Redis instead of Postgres? Change every function)
- Resource leaks (who closes the session?)

### With DI (Good)

```python
async def create_experiment(request: Request, service: ExperimentService):
    # Function receives what it needs - LOOSELY COUPLED
    return await service.create(request)
```

**Benefits**:
- Easy to test (inject a mock service)
- Easy to change (swap implementations in one place)
- Resource management handled elsewhere

---

## 2. Why DI Matters

### The Wiring Problem

In any real application, you have layers:

```
┌─────────────────────────────────────────────────────┐
│                    HTTP Request                     │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                   Route Handler                     │
│        needs: Service, maybe Auth, maybe Config     │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                      Service                        │
│              needs: Repository, maybe Cache         │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                    Repository                       │
│                  needs: DB Session                  │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                    Database                         │
└─────────────────────────────────────────────────────┘
```

**Without DI**: You manually wire all these connections in every route. Spaghetti.

**With DI**: FastAPI builds this graph automatically. Clean.

---

## 3. The Core Mental Model

### FastAPI DI is NOT Magic

It's literally:

> **"Build a directed graph of function calls before hitting my endpoint."**

When you write:

```python
@router.get("/experiments/{id}")
async def get_experiment(id: str, service: ExperimentServiceDep):
    ...
```

FastAPI thinks:

```
"I need to call get_experiment(id, service)"
"id comes from the URL path ✓"
"service needs Depends(get_experiment_service)..."
"   → get_experiment_service needs Depends(get_session)..."
"      → get_session has no dependencies, I can call it first!"
```

Then it executes **bottom-up**:

```
1. Call get_session() → get AsyncSession
2. Call get_experiment_service(session) → get ExperimentService
3. Call get_experiment(id, service) → your route runs
```

---

## 4. The Three Primitives

There are exactly **three patterns** you need to understand.

---

### 4.1 Simple Dependencies

> **Use for**: Static values, configs, feature flags, anything without cleanup

#### Pattern

```python
def get_something():
    return SomeValue()
```

#### Characteristics

| Aspect | Behavior |
|--------|----------|
| Returns | A value directly |
| Cleanup | None needed |
| When to use | Configs, settings, static data |

#### Example: Configuration Dependency

```python
# dependencies.py
from app.core.configuration import Settings

def get_settings() -> Settings:
    return Settings(
        model_type="matrix_factorization",
        n_factors=50,
        learning_rate=0.01
    )

# routes.py
@router.post("/train")
async def train_model(settings: Annotated[Settings, Depends(get_settings)]):
    print(f"Training with {settings.n_factors} factors")
```

#### FedRec Status

> Currently not used in FedRec, but would be useful for injecting:
> - Feature flags (enable/disable federated learning)
> - Model hyperparameter defaults
> - External API credentials

---

### 4.2 Contextual Dependencies (yield)

> **Use for**: Resources that need setup AND teardown (open/close, begin/commit)

#### Pattern

```python
async def get_resource():
    resource = acquire_resource()  # Setup
    try:
        yield resource             # Pause here, let route run
    finally:
        release_resource()         # Cleanup (always runs)
```

#### Characteristics

| Aspect | Behavior |
|--------|----------|
| Returns | Uses `yield` (generator) |
| Cleanup | Code after `yield` runs after route completes |
| When to use | DB sessions, file handles, connections, transactions |

#### The yield Lifecycle

```
┌──────────────────────────────────────────────────────────┐
│ 1. FastAPI calls get_session()                           │
│    → Code BEFORE yield runs (open session)               │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 2. yield session                                         │
│    → FastAPI receives session                            │
│    → Function PAUSES here                                │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Your route runs with the session                      │
│    → Query database, create records, etc.                │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Route completes (success or error)                    │
│    → FastAPI resumes get_session()                       │
│    → Code AFTER yield runs (commit or rollback)          │
└──────────────────────────────────────────────────────────┘
```

#### Real FedRec Example: Database Session

**File**: `app/infrastructure/database.py` (lines 69-82)

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session                    # ← Route runs with this session
            await session.commit()           # ← Success: commit transaction
        except Exception:
            await session.rollback()         # ← Error: rollback transaction
            raise
```

**What this does**:

| Phase | What Happens |
|-------|--------------|
| Before yield | Creates session, opens connection |
| yield | Passes session to route, pauses |
| After yield (success) | Commits all changes to DB |
| After yield (error) | Rolls back all changes |

**Why this is powerful**:

```python
@router.post("/experiments")
async def create_experiment(request: Request, db: Annotated[AsyncSession, Depends(get_session)]):
    # You don't think about commits or rollbacks
    # Just use the session - cleanup is automatic
    repo = ExperimentRepository(db)
    await repo.add(experiment)
    # If this line raises an error → automatic rollback
    # If route completes normally → automatic commit
```

---

### 4.3 Nested Dependencies (composition)

> **Use for**: Building complex objects that depend on simpler objects

#### Pattern

```python
def get_complex_thing(
    simple_thing: Annotated[SimpleThing, Depends(get_simple_thing)]
) -> ComplexThing:
    return ComplexThing(simple_thing)
```

#### Characteristics

| Aspect | Behavior |
|--------|----------|
| Parameters | Other dependencies via `Depends()` |
| Resolution | FastAPI resolves dependencies recursively |
| When to use | Services that need repos, repos that need sessions |

#### The Dependency Chain

```
get_experiment_service
        │
        │ needs
        ▼
    get_session
        │
        │ needs
        ▼
      (nothing)
```

FastAPI resolves **bottom-up**:
1. `get_session()` has no dependencies → call it first
2. `get_experiment_service(session)` → now we can call it

#### Real FedRec Example: Experiment Service

**File**: `app/api/dependencies.py` (lines 13-26)

```python
def get_experiment_service(
    db: Annotated[AsyncSession, Depends(get_session)]  # ← Nested dependency!
) -> ExperimentService:
    """Dependency injection for experiment service."""
    experiment_repo = ExperimentRepository(db)    # Uses the injected session
    metrics_repo = MetricsRepository(db)          # Same session instance
    return ExperimentService(experiment_repo, metrics_repo)
```

**Visual breakdown**:

```
┌─────────────────────────────────────────────────────────────┐
│ get_experiment_service(db)                                  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ db: AsyncSession ← comes from Depends(get_session)  │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ ExperimentRepository(db)                            │   │
│   │ MetricsRepository(db)      ← Same session!          │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ return ExperimentService(exp_repo, metrics_repo)    │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: Both repositories share the **same session instance**. This means:
- All queries in one request use one transaction
- Commit/rollback affects all operations together
- No connection pool exhaustion

---

## 5. Real Examples from FedRec

### Complete Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROUTES                                   │
│  experiments.py, metrics.py                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ExperimentServiceDep    MetricsServiceDep               │    │
│  └──────────────┬───────────────────┬──────────────────────┘    │
└─────────────────┼───────────────────┼───────────────────────────┘
                  │                   │
                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DEPENDENCIES                                │
│  dependencies.py                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ get_experiment_service()    get_metrics_service()       │    │
│  │         │                           │                   │    │
│  │         └───────────┬───────────────┘                   │    │
│  │                     │                                   │    │
│  │                     ▼                                   │    │
│  │           Depends(get_session)                          │    │
│  └─────────────────────┬───────────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE                                    │
│  database.py                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ get_session() → yield AsyncSession                      │    │
│  │     └── get_session_factory()                           │    │
│  │             └── get_engine()                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Type Alias Pattern

**File**: `app/api/routes/experiments.py` (line 22)

```python
# Instead of writing this every time:
service: Annotated[ExperimentService, Depends(get_experiment_service)]

# Define a type alias once:
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]

# Use it cleanly:
async def create_experiment(request: Request, service: ExperimentServiceDep):
    ...
```

**Benefits**:
- Cleaner route signatures
- Single source of truth
- Easy to refactor

---

## 6. Common Patterns

### Pattern 1: Service per Request

Each HTTP request gets fresh instances:

```
Request 1: get_session() → Session A → Service A
Request 2: get_session() → Session B → Service B
```

No shared state between requests.

### Pattern 2: Shared Session Across Repos

```python
def get_experiment_service(db: Annotated[AsyncSession, Depends(get_session)]):
    exp_repo = ExperimentRepository(db)     # ← Same db
    metrics_repo = MetricsRepository(db)    # ← Same db
    return ExperimentService(exp_repo, metrics_repo)
```

All repositories in one service share the same transaction.

### Pattern 3: Interface-Based Injection

**Service depends on interface, not implementation**:

```python
# Service (app/application/services/experiment_service.py)
class ExperimentService:
    def __init__(
        self,
        experiment_repository: IExperimentRepository,  # ← Interface
        metrics_repository: IMetricsRepository,        # ← Interface
    ):
        ...

# Dependency wires the concrete implementation
def get_experiment_service(db: ...):
    return ExperimentService(
        ExperimentRepository(db),  # ← Concrete
        MetricsRepository(db),     # ← Concrete
    )
```

**Why**: You can swap `ExperimentRepository` for `MockExperimentRepository` in tests.

---

## 7. Quick Reference

### Cheat Sheet

| I need to inject... | Use this pattern |
|---------------------|------------------|
| Static config/settings | Simple dependency (return value) |
| Database session | Contextual dependency (yield) |
| File handle | Contextual dependency (yield) |
| Service with repos | Nested dependency (Depends in params) |
| Repository with session | Nested dependency (Depends in params) |

### Syntax Reference

```python
from typing import Annotated
from fastapi import Depends

# Simple
def get_config() -> Config:
    return Config()

# Contextual (yield)
async def get_session() -> AsyncGenerator[Session, None]:
    session = Session()
    try:
        yield session
    finally:
        session.close()

# Nested
def get_service(
    db: Annotated[Session, Depends(get_session)]
) -> Service:
    return Service(Repository(db))

# In route
@router.get("/items")
async def get_items(service: Annotated[Service, Depends(get_service)]):
    return await service.get_all()

# With type alias (cleaner)
ServiceDep = Annotated[Service, Depends(get_service)]

@router.get("/items")
async def get_items(service: ServiceDep):
    return await service.get_all()
```

### Mental Checklist

When writing a new route, ask:

1. What does this route need? (service, config, auth?)
2. Do I have a dependency function for it?
3. Is the dependency using `yield` if it needs cleanup?
4. Am I using `Annotated[Type, Depends(func)]` syntax?

---

## Summary

| Concept | One-liner |
|---------|-----------|
| **DI** | Functions receive dependencies, don't create them |
| **Simple** | `return value` - for static stuff |
| **Contextual** | `yield value` - for stuff needing cleanup |
| **Nested** | `Depends()` in params - for composition |
| **Resolution** | FastAPI builds dependency graph, resolves bottom-up |

---

> **Next**: See `2026-01-21-FastAPI_DI_Step_By_Step_Traces.md` for detailed traces of how DI resolves for specific routes.
