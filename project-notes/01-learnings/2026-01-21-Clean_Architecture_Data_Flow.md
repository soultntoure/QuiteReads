# Clean Architecture - Complete Data Flow

> **Purpose**: Understand how data flows through the layers of the FedRec Dashboard, from HTTP request to database and back.

---

## Table of Contents

1. [The Layer Chain](#1-the-layer-chain)
2. [Complete Flow (Both Directions)](#2-complete-flow-both-directions)
3. [Data Transformations](#3-data-transformations)
4. [Concrete Example: POST /experiments/centralized](#4-concrete-example-post-experimentscentralized)
5. [Layer Responsibilities](#5-layer-responsibilities)
6. [Why This Separation?](#6-why-this-separation)

---

## 1. The Layer Chain

The basic dependency chain:

```
Database ← Repo ← Service ← API ← Client
```

Reading it:
- A **Repo** needs a **Database** (session)
- A **Service** needs a **Repo**
- The **API** needs a **Service** to handle requests
- The **API** fulfills the request and the **Client** gets the response

---

## 2. Complete Flow (Both Directions)

### Request Flow (→)
*"Client wants to create an experiment"*

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLIENT  │───►│   API    │───►│ SERVICE  │───►│   REPO   │───►│ DATABASE │
│          │    │ (Route)  │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     │  HTTP POST    │  Pydantic     │  Domain       │  ORM Model    │  SQL
     │  JSON body    │  Schema       │  Entity       │               │  INSERT
     │               │               │               │               │
```

### Response Flow (←)
*"Client receives the created experiment"*

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLIENT  │◄───│   API    │◄───│ SERVICE  │◄───│   REPO   │◄───│ DATABASE │
│          │    │ (Route)  │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     │  HTTP 201     │  Pydantic     │  Domain       │  ORM Model    │  Row
     │  JSON         │  Response     │  Entity       │               │  data
```

---

## 3. Data Transformations

Each layer has its **own data type**. Data transforms as it flows:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER        │  DATA TYPE              │  YOUR CODE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Client       │  JSON                   │  {"name": "Test", "n_factors": 50}   │
│       ↓       │                         │                                       │
│  API          │  Pydantic Schema        │  CreateCentralizedExperimentRequest  │
│       ↓       │  (validated)            │                                       │
│  Service      │  Domain Entity          │  CentralizedExperiment               │
│       ↓       │  (business rules)       │                                       │
│  Repo         │  ORM Model              │  ExperimentModel                      │
│       ↓       │  (database mapping)     │                                       │
│  Database     │  SQL / Rows             │  INSERT INTO experiments ...          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Key Insight

Data is **never** passed directly from Client to Database. It goes through transformations:

```
JSON → Pydantic Schema → Domain Entity → ORM Model → SQL
```

Each transformation adds:
- **Validation** (Pydantic catches invalid input)
- **Business rules** (Domain enforces constraints)
- **Persistence mapping** (ORM handles database specifics)

---

## 4. Concrete Example: POST /experiments/centralized

### Step-by-Step with FedRec Code

```
STEP 1: Client sends JSON
────────────────────────────────────────────────────────────────
POST /experiments/centralized
{"name": "MF Test", "n_factors": 50, "learning_rate": 0.01}


STEP 2: API Layer - Validate & Convert to Schema
────────────────────────────────────────────────────────────────
File: app/api/routes/experiments.py:26

async def create_centralized_experiment(
    request: CreateCentralizedExperimentRequest,  ← Pydantic validates JSON
    service: ExperimentServiceDep
):
    # request is now a validated Pydantic object
    # request.name = "MF Test"
    # request.n_factors = 50


STEP 3: API Layer - Convert Schema to Domain Config
────────────────────────────────────────────────────────────────
File: app/api/routes/experiments.py:28-31

    experiment = await service.create_centralized_experiment(
        name=request.name,
        config=request.to_domain_config(),  ← Schema → Domain Configuration
    )


STEP 4: Service Layer - Create Domain Entity
────────────────────────────────────────────────────────────────
File: app/application/services/experiment_service.py:59-66

    experiment = CentralizedExperiment(      ← Domain Entity created
        experiment_id=str(uuid4()),
        name=name,
        config=config,
        status=ExperimentStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )


STEP 5: Service Layer - Ask Repo to Persist
────────────────────────────────────────────────────────────────
File: app/application/services/experiment_service.py:67-68

    await self._experiment_repo.add(experiment)  ← Pass domain entity to repo
    return experiment


STEP 6: Repo Layer - Convert Domain → ORM Model
────────────────────────────────────────────────────────────────
File: app/infrastructure/repositories/experiment_repository.py:54-58

    model = self._to_model(entity)  ← Domain Entity → ORM Model
    self._session.add(model)        ← Add to SQLAlchemy session
    await self._session.flush()     ← Execute INSERT (not committed yet)


STEP 7: Database Layer - SQL Executed
────────────────────────────────────────────────────────────────
INSERT INTO experiments (id, name, experiment_type, status, config, ...)
VALUES ('uuid...', 'MF Test', 'centralized', 'pending', '{...}', ...)


STEP 8: Response flows back
────────────────────────────────────────────────────────────────
Repo returns: Domain Entity (same one)
       ↓
Service returns: Domain Entity
       ↓
API converts: ExperimentResponse.from_domain(experiment)  ← Domain → Schema
       ↓
FastAPI serializes: Pydantic Schema → JSON
       ↓
Client receives: {"experiment_id": "...", "name": "MF Test", ...}
```

---

## 5. Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   CLIENT                                                                     │
│   └── Sends HTTP requests, receives JSON responses                          │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   API LAYER (routes + schemas)                                               │
│   ├── Validates input (Pydantic schemas)                                    │
│   ├── Converts schemas ↔ domain objects                                     │
│   ├── Returns proper HTTP status codes                                      │
│   └── Knows NOTHING about database                                          │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SERVICE LAYER                                                              │
│   ├── Contains business logic                                               │
│   ├── Enforces rules (can't complete a PENDING experiment)                  │
│   ├── Orchestrates multiple repos if needed                                 │
│   └── Knows NOTHING about HTTP or SQL                                       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   REPOSITORY LAYER                                                           │
│   ├── Converts domain entities ↔ ORM models                                 │
│   ├── Executes database operations                                          │
│   └── Knows NOTHING about HTTP or business rules                            │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   DATABASE                                                                   │
│   └── Stores data, executes SQL                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Each Layer Knows

| Layer | Knows About | Does NOT Know About |
|-------|-------------|---------------------|
| API | HTTP, Pydantic schemas | SQL, business rules |
| Service | Domain entities, business rules | HTTP, SQL |
| Repository | ORM models, SQL | HTTP, business rules |
| Database | Tables, rows, SQL | Everything else |

---

## 6. Why This Separation?

### Changeability

| Layer | Can change without affecting... |
|-------|--------------------------------|
| API schemas | Service, Repo, DB |
| Business rules (Service) | API, Repo, DB |
| Database (PostgreSQL → MySQL) | API, Service |
| ORM (SQLAlchemy → another) | API, Service |

### Real Example

**Scenario**: You want to switch from PostgreSQL to MongoDB.

**Without clean architecture**:
- Rewrite everything. SQL queries are scattered across routes, services, everywhere.

**With clean architecture**:
- Only change the Repository layer
- Create `MongoExperimentRepository` implementing `IExperimentRepository`
- Service and API remain untouched

```python
# Before (PostgreSQL)
def get_experiment_service(db: Annotated[AsyncSession, Depends(get_session)]):
    return ExperimentService(ExperimentRepository(db), ...)

# After (MongoDB) - only this file changes
def get_experiment_service(db: Annotated[MongoClient, Depends(get_mongo)]):
    return ExperimentService(MongoExperimentRepository(db), ...)
```

The `ExperimentService` doesn't change because it depends on `IExperimentRepository` (the interface), not the concrete implementation.

---

## Summary

```
┌────────────────────────────────────────────────────────────────────┐
│                        THE COMPLETE PICTURE                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Client ──JSON──► API ──Schema──► Service ──Entity──► Repo ──►DB  │
│                                                                    │
│  Client ◄──JSON── API ◄──Schema── Service ◄──Entity── Repo ◄──DB  │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  Each arrow is a DATA TRANSFORMATION                               │
│  Each layer has a SINGLE RESPONSIBILITY                            │
│  Each layer is ISOLATED from the others                            │
└────────────────────────────────────────────────────────────────────┘
```

---

> **Related**:
> - `2026-01-21-FastAPI_DI_Fundamentals.md` — How dependencies are injected
> - `2026-01-21-FastAPI_DI_Step_By_Step_Traces.md` — Detailed request traces
