# FastAPI DI - Step-by-Step Traces

> **Purpose**: Trace exactly how FastAPI resolves dependencies for real FedRec routes. Use this to debug DI issues or explain the flow to others.

---

## Table of Contents

1. [The Dependency Graph](#1-the-dependency-graph)
2. [Trace 1: GET /experiments/{id}](#2-trace-1-get-experimentsid)
3. [Trace 2: POST /experiments/centralized](#3-trace-2-post-experimentscentralized)
4. [Trace 3: DELETE /experiments/{id}](#4-trace-3-delete-experimentsid)
5. [Debugging Tips](#5-debugging-tips)

---

## 1. The Dependency Graph

Before tracing specific routes, understand the full dependency graph in FedRec.

### Visual: Complete Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HTTP REQUEST                                    │
│                    (POST, GET, DELETE, etc.)                                 │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ROUTE LAYER                                      │
│                                                                              │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│   │ experiments.py  │  │   metrics.py    │  │    health.py    │             │
│   └────────┬────────┘  └────────┬────────┘  └─────────────────┘             │
│            │                    │                                            │
│            │    Depends()       │    Depends()                               │
│            ▼                    ▼                                            │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │              ExperimentServiceDep / MetricsServiceDep        │           │
│   │                         (Type Aliases)                       │           │
│   └─────────────────────────────┬───────────────────────────────┘           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DEPENDENCY LAYER                                    │
│                         (dependencies.py)                                    │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │  get_experiment_service(db) → ExperimentService              │           │
│   │  get_metrics_service(db)    → MetricsService                 │           │
│   └─────────────────────────────┬───────────────────────────────┘           │
│                                 │                                            │
│                                 │  Depends(get_session)                      │
│                                 ▼                                            │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │  db: Annotated[AsyncSession, Depends(get_session)]          │           │
│   └─────────────────────────────┬───────────────────────────────┘           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATABASE LAYER                                      │
│                          (database.py)                                       │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────┐           │
│   │  get_session() → yield AsyncSession                          │           │
│   │       │                                                      │           │
│   │       ├── get_session_factory()                              │           │
│   │       │       └── get_engine()                               │           │
│   │       │               └── create_async_engine(DATABASE_URL)  │           │
│   │       │                                                      │           │
│   │       └── try/yield/finally (commit or rollback)             │           │
│   └─────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Resolution Order (Always Bottom-Up)

```
     ┌─────┐
     │  4  │  Route Handler (your code)
     └──▲──┘
        │
     ┌──┴──┐
     │  3  │  get_experiment_service()
     └──▲──┘
        │
     ┌──┴──┐
     │  2  │  get_session() [yield pauses here]
     └──▲──┘
        │
     ┌──┴──┐
     │  1  │  get_session_factory() / get_engine()
     └─────┘

     After route completes:

     ┌─────┐
     │  5  │  get_session() resumes → commit/rollback
     └─────┘
```

---

## 2. Trace 1: GET /experiments/{id}

> **Goal**: Retrieve a single experiment by its UUID

### Route Definition

**File**: `app/api/routes/experiments.py` (lines 75-79)

```python
@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str, service: ExperimentServiceDep):
    """Get a single experiment by ID"""
    experiment = await service.get_experiment_by_id(experiment_id)
    return ExperimentResponse.from_domain(experiment)
```

### Request Example

```
GET /experiments/a1b2c3d4-5678-90ab-cdef-1234567890ab
```

### Step-by-Step Trace

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 1: HTTP Request Arrives                                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  GET /experiments/a1b2c3d4-5678-90ab-cdef-1234567890ab                        ║
║                                                                                ║
║  FastAPI sees:                                                                 ║
║  - Route: @router.get("/{experiment_id}")                                     ║
║  - Handler: get_experiment(experiment_id: str, service: ExperimentServiceDep) ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 2: FastAPI Parses Parameters                                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Parameter: experiment_id                                                      ║
║  Source: Path parameter from URL                                               ║
║  Value: "a1b2c3d4-5678-90ab-cdef-1234567890ab"                                ║
║  Status: ✅ Resolved                                                           ║
║                                                                                ║
║  Parameter: service                                                            ║
║  Source: ExperimentServiceDep = Annotated[..., Depends(get_experiment_service)]║
║  Status: ⏳ Needs dependency resolution                                        ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 3: Resolve get_experiment_service                                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  File: app/api/dependencies.py:13-26                                          ║
║                                                                                ║
║  def get_experiment_service(                                                   ║
║      db: Annotated[AsyncSession, Depends(get_session)]  ← Nested dependency!  ║
║  ) -> ExperimentService:                                                       ║
║                                                                                ║
║  FastAPI sees:                                                                 ║
║  "I need to call get_experiment_service(db)"                                  ║
║  "But db requires Depends(get_session)..."                                    ║
║  "Let me resolve get_session FIRST"                                           ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 4: Resolve get_session (FIRST dependency to actually execute)           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  File: app/infrastructure/database.py:69-82                                   ║
║                                                                                ║
║  async def get_session() -> AsyncGenerator[AsyncSession, None]:               ║
║      session_factory = get_session_factory()                                  ║
║      async with session_factory() as session:                                 ║
║          try:                                                                 ║
║              yield session  ← PAUSE HERE, return session to caller            ║
║              await session.commit()                                           ║
║          except Exception:                                                    ║
║              await session.rollback()                                         ║
║              raise                                                            ║
║                                                                                ║
║  Execution:                                                                    ║
║  1. get_session_factory() → returns async_sessionmaker                        ║
║  2. session_factory() → creates new AsyncSession                              ║
║  3. yield session → PAUSES, gives session to FastAPI                          ║
║                                                                                ║
║  Result: AsyncSession instance (connected to PostgreSQL)                      ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │  session passed up
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 5: Execute get_experiment_service(db=session)                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Now FastAPI has the session, it can call:                                    ║
║                                                                                ║
║  def get_experiment_service(db: AsyncSession):                                ║
║      experiment_repo = ExperimentRepository(db)  ← Uses session               ║
║      metrics_repo = MetricsRepository(db)        ← Same session instance      ║
║      return ExperimentService(experiment_repo, metrics_repo)                  ║
║                                                                                ║
║  Execution:                                                                    ║
║  1. Create ExperimentRepository with session                                  ║
║  2. Create MetricsRepository with SAME session                                ║
║  3. Create ExperimentService with both repos                                  ║
║  4. Return service                                                            ║
║                                                                                ║
║  Result: ExperimentService instance (with repos wired to session)             ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │  service passed to route
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 6: Execute Route Handler                                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  All dependencies resolved! FastAPI calls:                                    ║
║                                                                                ║
║  await get_experiment(                                                        ║
║      experiment_id="a1b2c3d4-5678-90ab-cdef-1234567890ab",                    ║
║      service=<ExperimentService instance>                                     ║
║  )                                                                            ║
║                                                                                ║
║  Your code runs:                                                              ║
║  1. service.get_experiment_by_id(experiment_id)                               ║
║     └── repo.get_by_id(experiment_id)                                         ║
║         └── SELECT * FROM experiments WHERE id = ?                            ║
║  2. ExperimentResponse.from_domain(experiment)                                ║
║  3. Return response                                                           ║
║                                                                                ║
║  Result: ExperimentResponse (Pydantic model → JSON)                           ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 7: Cleanup - get_session() Resumes                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Route completed successfully → get_session() resumes after yield:            ║
║                                                                                ║
║  async def get_session():                                                     ║
║      ...                                                                      ║
║          try:                                                                 ║
║              yield session                                                    ║
║              await session.commit()  ← EXECUTES NOW (success path)            ║
║          except Exception:                                                    ║
║              await session.rollback()                                         ║
║              raise                                                            ║
║                                                                                ║
║  Execution:                                                                    ║
║  1. await session.commit() → commits transaction                              ║
║  2. Session context manager closes → connection returned to pool              ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 8: HTTP Response Sent                                                   ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  HTTP/1.1 200 OK                                                              ║
║  Content-Type: application/json                                               ║
║                                                                                ║
║  {                                                                            ║
║    "experiment_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",                   ║
║    "name": "Federated MF Test",                                               ║
║    "experiment_type": "federated",                                            ║
║    "status": "completed",                                                     ║
║    ...                                                                        ║
║  }                                                                            ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Timeline View

```
Time ──────────────────────────────────────────────────────────────────────────►

     │ Request    │ get_session │ get_exp_svc │  Route    │ Cleanup │ Response
     │ arrives    │ yields      │ returns     │  runs     │ commit  │ sent
     │            │             │             │           │         │
     ▼            ▼             ▼             ▼           ▼         ▼
─────●────────────●─────────────●─────────────●───────────●─────────●──────────
     │            │             │             │           │
     │◄──────────►│◄───────────►│◄───────────►│◄─────────►│
     │  ~1ms      │   ~1ms      │   ~5ms      │   ~1ms    │
     │  setup     │   create    │   DB query  │  cleanup  │
                  │   repos     │   + response│           │
```

---

## 3. Trace 2: POST /experiments/centralized

> **Goal**: Create a new centralized experiment

### Route Definition

**File**: `app/api/routes/experiments.py` (lines 25-32)

```python
@router.post("/centralized", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_centralized_experiment(request: CreateCentralizedExperimentRequest, service: ExperimentServiceDep):
    """Create a new centralized experiment"""
    experiment = await service.create_centralized_experiment(
        name=request.name,
        config=request.to_domain_config(),
    )
    return ExperimentResponse.from_domain(experiment)
```

### Request Example

```
POST /experiments/centralized
Content-Type: application/json

{
  "name": "MF Baseline",
  "n_factors": 50,
  "learning_rate": 0.01,
  "regularization": 0.02,
  "n_epochs": 20
}
```

### Step-by-Step Trace

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 1: HTTP Request Arrives                                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  POST /experiments/centralized                                                 ║
║  Body: {"name": "MF Baseline", "n_factors": 50, ...}                          ║
║                                                                                ║
║  FastAPI sees:                                                                 ║
║  - Route: @router.post("/centralized")                                        ║
║  - Handler: create_centralized_experiment(request, service)                   ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 2: Parse and Validate Request Body                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Parameter: request                                                            ║
║  Type: CreateCentralizedExperimentRequest (Pydantic model)                    ║
║                                                                                ║
║  Pydantic validation:                                                          ║
║  ✅ name: "MF Baseline" (str, required)                                        ║
║  ✅ n_factors: 50 (int, default=50)                                            ║
║  ✅ learning_rate: 0.01 (float, default=0.01)                                  ║
║  ✅ regularization: 0.02 (float, default=0.02)                                 ║
║  ✅ n_epochs: 20 (int, default=10)                                             ║
║                                                                                ║
║  If validation fails → 422 Unprocessable Entity (before any DI happens!)      ║
║                                                                                ║
║  Status: ✅ Resolved                                                           ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 3: Resolve Dependencies (same as GET trace)                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │  3a. get_session()                                                      │  ║
║  │      → Creates AsyncSession                                             │  ║
║  │      → yield session (PAUSE)                                            │  ║
║  └─────────────────────────────────┬───────────────────────────────────────┘  ║
║                                    │ session                                  ║
║                                    ▼                                          ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │  3b. get_experiment_service(db=session)                                 │  ║
║  │      → ExperimentRepository(session)                                    │  ║
║  │      → MetricsRepository(session)                                       │  ║
║  │      → return ExperimentService(repos)                                  │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 4: Execute Route Handler                                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  await create_centralized_experiment(                                         ║
║      request=CreateCentralizedExperimentRequest(...),                         ║
║      service=<ExperimentService>                                              ║
║  )                                                                            ║
║                                                                                ║
║  Execution flow:                                                               ║
║                                                                                ║
║  1. request.to_domain_config()                                                ║
║     └── Converts Pydantic schema → Domain Configuration                       ║
║                                                                                ║
║  2. service.create_centralized_experiment(name, config)                       ║
║     │                                                                         ║
║     ├── Creates CentralizedExperiment domain entity                           ║
║     │   └── experiment_id = uuid4()                                           ║
║     │   └── status = PENDING                                                  ║
║     │   └── created_at = now()                                                ║
║     │                                                                         ║
║     └── repo.add(experiment)                                                  ║
║         └── INSERT INTO experiments (id, name, ...) VALUES (?, ?, ...)        ║
║         └── session.flush() (not committed yet!)                              ║
║                                                                                ║
║  3. ExperimentResponse.from_domain(experiment)                                ║
║     └── Convert domain entity → Pydantic response                             ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 5: Cleanup - COMMIT Transaction                                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Route completed successfully!                                                 ║
║                                                                                ║
║  get_session() resumes:                                                        ║
║      yield session                                                            ║
║      await session.commit()  ← THE INSERT IS NOW PERSISTED TO DB              ║
║                                                                                ║
║  The experiment now exists in PostgreSQL.                                     ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 6: HTTP Response                                                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  HTTP/1.1 201 Created                                                         ║
║  Content-Type: application/json                                               ║
║                                                                                ║
║  {                                                                            ║
║    "experiment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",                   ║
║    "name": "MF Baseline",                                                     ║
║    "experiment_type": "centralized",                                          ║
║    "status": "pending",                                                       ║
║    "created_at": "2026-01-21T10:30:00Z",                                      ║
║    "config": {                                                                ║
║      "n_factors": 50,                                                         ║
║      "learning_rate": 0.01,                                                   ║
║      "regularization": 0.02,                                                  ║
║      "n_epochs": 20                                                           ║
║    }                                                                          ║
║  }                                                                            ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Error Scenario: Validation Fails

```
POST /experiments/centralized
Body: {"name": "Test", "n_factors": -5}  ← Invalid!

╔═══════════════════════════════════════════════════════════════════════════════╗
║  Pydantic Validation                                                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ❌ n_factors: -5 fails validation (must be positive)                         ║
║                                                                                ║
║  FastAPI returns 422 BEFORE any DI happens:                                   ║
║  - No get_session() called                                                    ║
║  - No database connection opened                                              ║
║  - No service created                                                         ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝

HTTP/1.1 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "n_factors"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## 4. Trace 3: DELETE /experiments/{id}

> **Goal**: Delete an experiment and its associated metrics

### Route Definition

**File**: `app/api/routes/experiments.py` (lines 108-112)

```python
@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: str, service: ExperimentServiceDep):
    """Delete an experiment"""
    await service.delete_experiment(experiment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### Request Example

```
DELETE /experiments/a1b2c3d4-5678-90ab-cdef-1234567890ab
```

### Step-by-Step Trace (Happy Path)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 1-3: Request + DI Resolution (same pattern)                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  DELETE /experiments/a1b2c3d4-5678-90ab-cdef-1234567890ab                     ║
║                                                                                ║
║  1. Parse path: experiment_id = "a1b2c3d4-..."                                ║
║  2. get_session() → yield session                                             ║
║  3. get_experiment_service(session) → ExperimentService                       ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 4: Execute Route Handler                                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  await delete_experiment(                                                      ║
║      experiment_id="a1b2c3d4-...",                                            ║
║      service=<ExperimentService>                                              ║
║  )                                                                            ║
║                                                                                ║
║  service.delete_experiment(experiment_id):                                    ║
║  │                                                                            ║
║  ├── 1. metrics_repo.delete_by_experiment(experiment_id)                      ║
║  │       └── DELETE FROM metrics WHERE experiment_id = ?                      ║
║  │       └── Returns: 15 metrics deleted                                      ║
║  │                                                                            ║
║  └── 2. experiment_repo.delete(experiment_id)                                 ║
║          └── SELECT * FROM experiments WHERE id = ?                           ║
║          └── Experiment found ✅                                               ║
║          └── DELETE FROM experiments WHERE id = ?                             ║
║          └── session.flush()                                                  ║
║                                                                                ║
║  Both DELETEs are in the SAME transaction (same session)!                     ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 5: Cleanup - COMMIT                                                     ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  get_session() resumes:                                                        ║
║      await session.commit()                                                   ║
║                                                                                ║
║  BOTH deletes are committed atomically:                                       ║
║  - Either both succeed                                                        ║
║  - Or both are rolled back                                                    ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 6: HTTP Response                                                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  HTTP/1.1 204 No Content                                                      ║
║  (empty body)                                                                 ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Error Scenario: Experiment Not Found

```
DELETE /experiments/nonexistent-id-12345

╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 4: Route Handler - Error                                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  service.delete_experiment("nonexistent-id-12345"):                           ║
║  │                                                                            ║
║  └── experiment_repo.delete(experiment_id)                                    ║
║          └── SELECT * FROM experiments WHERE id = ?                           ║
║          └── Result: None (not found)                                         ║
║          └── raise EntityNotFoundError("Experiment not found")                ║
║                                                                                ║
║  Exception propagates up!                                                      ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 5: Cleanup - ROLLBACK                                                   ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Exception raised! get_session() resumes in except block:                     ║
║                                                                                ║
║  async def get_session():                                                     ║
║      ...                                                                      ║
║          try:                                                                 ║
║              yield session                                                    ║
║              await session.commit()                                           ║
║          except Exception:                                                    ║
║              await session.rollback()  ← EXECUTES (exception path)            ║
║              raise                     ← Re-raises the exception              ║
║                                                                                ║
║  Any partial changes (like metrics deleted) are ROLLED BACK.                  ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 6: Exception Handler Catches Error                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  File: app/api/main.py (exception handler)                                    ║
║                                                                                ║
║  @app.exception_handler(EntityNotFoundError)                                  ║
║  async def entity_not_found_handler(request, exc):                            ║
║      return JSONResponse(                                                     ║
║          status_code=404,                                                     ║
║          content={"detail": str(exc)}                                         ║
║      )                                                                        ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STEP 7: HTTP Response (Error)                                                ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  HTTP/1.1 404 Not Found                                                       ║
║  Content-Type: application/json                                               ║
║                                                                                ║
║  {                                                                            ║
║    "detail": "Experiment with id nonexistent-id-12345 not found"             ║
║  }                                                                            ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Why Rollback Matters

```
Scenario: Delete experiment with 100 associated metrics

Timeline WITHOUT proper transaction handling:
1. DELETE 50 metrics ✅
2. Error occurs! 💥
3. 50 metrics are orphaned (deleted but experiment still exists)

Timeline WITH get_session() rollback:
1. DELETE 50 metrics (in transaction, not committed)
2. Error occurs! 💥
3. ROLLBACK → 50 metrics are restored
4. Database is in consistent state ✅
```

---

## 5. Debugging Tips

### Tip 1: Add Logging to Dependencies

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    print(f"[DI] Creating session")  # Debug log
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            print(f"[DI] Yielding session {id(session)}")
            yield session
            print(f"[DI] Committing session {id(session)}")
            await session.commit()
        except Exception as e:
            print(f"[DI] Rolling back session {id(session)}: {e}")
            await session.rollback()
            raise
```

### Tip 2: Verify Same Session Instance

```python
def get_experiment_service(db: Annotated[AsyncSession, Depends(get_session)]):
    print(f"[DI] Session ID: {id(db)}")
    exp_repo = ExperimentRepository(db)
    print(f"[DI] ExpRepo session ID: {id(exp_repo._session)}")
    metrics_repo = MetricsRepository(db)
    print(f"[DI] MetricsRepo session ID: {id(metrics_repo._session)}")
    # All three should print the SAME ID
```

### Tip 3: Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Session is closed" | Using session after request ends | Don't store session in global state |
| Different data in repos | Multiple sessions created | Ensure single `Depends(get_session)` |
| Changes not persisted | Missing commit | Check `get_session()` has `await session.commit()` |
| Partial changes on error | Missing rollback | Check `get_session()` has try/except/rollback |

### Tip 4: Visualize with `/docs`

1. Run: `uvicorn app.api.main:app --reload`
2. Open: `http://localhost:8000/docs`
3. Try endpoints and watch server logs

---

## Summary: The Three Traces Compared

| Aspect | GET | POST | DELETE |
|--------|-----|------|--------|
| **Input** | Path param | JSON body + validation | Path param |
| **DI** | Same pattern | Same pattern | Same pattern |
| **DB Ops** | SELECT | INSERT | DELETE (multiple) |
| **Success** | 200 + JSON | 201 + JSON | 204 (no body) |
| **Cleanup** | Commit (no changes) | Commit (INSERT persisted) | Commit (DELETEs persisted) |
| **Error** | 404 + rollback | 422 (no DI) or 500 + rollback | 404 + rollback |

**Key Insight**: The DI resolution pattern is **identical** for all routes. Only the HTTP method, inputs, and business logic differ.

---

> **Related**: See `2026-01-21-FastAPI_DI_Fundamentals.md` for the conceptual foundation.
