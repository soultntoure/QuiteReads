# QuiteReads Dashboard - Architecture Canvas

> **A visual mental model connecting all architectural components**

## 🎯 System Overview

QuiteReads Dashboard implements a federated learning book recommender system comparing centralized vs federated matrix factorization approaches.

**Tech Stack**: Python 3.12 | FastAPI | SQLAlchemy (async) | PostgreSQL | PyTorch Lightning | Flower Framework

---

## 🏗️ Clean Architecture Layers

```mermaid
graph TB
    subgraph "API Layer (Presentation)"
        A1[FastAPI Routes]
        A2[Pydantic Schemas]
        A3[Dependencies]
    end

    subgraph "Application Layer (Use Cases)"
        B1[Experiment Manager]
        B2[Centralized Trainer]
        B3[Federated Simulation Manager]
        B4[Data Handler]
        B5[Metrics Calculator]
        B6[Metrics Logger]
        B7[Application Services]
    end

    subgraph "Core Domain (Business Logic)"
        C1[Experiment Entities]
        C2[Configuration]
        C3[Metrics Models]
        C4[Repository Interfaces]
        C5[State Machine]
    end

    subgraph "Infrastructure Layer (External Concerns)"
        D1[SQLAlchemy ORM]
        D2[Repository Implementations]
        D3[Database Connection]
    end

    subgraph "External Systems"
        E1[(PostgreSQL)]
        E2[Flower Framework]
        E3[File System]
    end

    A1 --> B1
    A1 --> B7
    A2 -.validates.-> A1
    A3 -.injects.-> B7

    B1 --> C1
    B1 --> B2
    B1 --> B3
    B2 --> C1
    B3 --> C1
    B4 --> C2
    B5 --> C3
    B6 --> C3
    B7 --> C4

    C1 --> C5
    C1 --> C2
    C4 -.defines interface.-> D2

    D2 --> D1
    D2 --> D3
    D1 --> E1
    B3 --> E2
    B4 --> E3

    style C1 fill:#ff9999
    style C4 fill:#ff9999
    style B1 fill:#99ccff
    style D2 fill:#99ff99
    style A1 fill:#ffff99
```

**Dependency Rule**: Inner layers (Core) know nothing about outer layers (Infrastructure, API). Dependencies point INWARD.

---

## 🔄 Complete Data Flow

```mermaid
sequenceDiagram
    participant U as User/Frontend
    participant API as API Layer
    participant EM as Experiment Manager
    participant T as Trainer (Central/Fed)
    participant ML as Metrics Logger
    participant R as Repository
    participant DB as PostgreSQL

    U->>API: POST /experiments (config)
    API->>API: Validate schema
    API->>EM: create_experiment()

    EM->>EM: Create domain entity
    EM->>R: save(experiment)
    R->>DB: INSERT experiment (PENDING)

    EM->>EM: mark_running()
    EM->>R: update(experiment)
    R->>DB: UPDATE status=RUNNING

    EM->>T: train_model(config)

    loop Each Epoch/Round
        T->>T: Train step
        T->>ML: log_metric(epoch, rmse, mae)
        ML->>R: save_metric()
        R->>DB: INSERT metric
    end

    T-->>EM: Final metrics
    EM->>EM: mark_completed(metrics)
    EM->>R: update(experiment)
    R->>DB: UPDATE status=COMPLETED

    EM-->>API: Experiment result
    API-->>U: 200 OK (experiment_id)

    U->>API: GET /experiments/{id}
    API->>R: get_by_id(id)
    R->>DB: SELECT experiment
    API->>R: get_metrics(id)
    R->>DB: SELECT metrics
    API-->>U: 200 OK (with timeline)
```

---

## 📦 Directory Structure & Responsibilities

```
quitereads-dashboard/
│
├── app/
│   ├── core/                          # 🔴 DOMAIN LAYER (Business Rules)
│   │   ├── experiments.py             # Experiment entities + state machine
│   │   ├── entities.py                # Dataset, Rating, LocalUserData
│   │   ├── configuration.py           # Hyperparameter models
│   │   ├── metrics.py                 # Domain metrics models
│   │   ├── repositories/
│   │   │   └── interfaces.py          # Repository contracts (abstractions)
│   │   └── models/
│   │       └── recommender.py         # Matrix factorization interface
│   │
│   ├── application/                   # 🔵 APPLICATION LAYER (Use Cases)
│   │   ├── experiment_manager.py      # Main orchestrator
│   │   ├── training/
│   │   │   ├── centralized_trainer.py # Surprise-based training
│   │   │   └── federated_simulation_manager.py  # Flower simulation
│   │   ├── data/
│   │   │   └── data_handler.py        # Dataset loading/preprocessing
│   │   ├── reporting/
│   │   │   ├── metrics_calculator.py  # RMSE/MAE computation
│   │   │   └── metrics_logger.py      # Per-epoch logging
│   │   └── services/                  # Application services
│   │
│   ├── infrastructure/                # 🟢 INFRASTRUCTURE LAYER (Adapters)
│   │   ├── database.py                # SQLAlchemy engine + session factory
│   │   ├── models.py                  # ORM models (DB tables)
│   │   └── repositories/
│   │       ├── base_repository.py     # Generic CRUD operations
│   │       ├── experiment_repository.py
│   │       └── metrics_repository.py
│   │
│   ├── api/                           # 🟡 API LAYER (Presentation)
│   │   ├── main.py                    # FastAPI app + middleware
│   │   ├── routes/
│   │   │   ├── experiments.py         # Experiment CRUD endpoints
│   │   │   ├── metrics.py             # Metrics retrieval
│   │   │   └── health.py              # Health check
│   │   ├── schemas/                   # Pydantic request/response models
│   │   └── dependencies.py            # Dependency injection
│   │
│   ├── federated/                     # Flower FL implementation
│   │   ├── partitioner.py             # IID user-based partitioning
│   │   ├── strategy.py                # FedAvgItemsOnly (aggregate items only)
│   │   ├── client_app.py              # Flower client
│   │   └── server_app.py              # Flower server
│   │
│   └── utils/                         # Cross-cutting concerns
│       ├── exceptions.py              # Custom exceptions
│       └── logging.py                 # Logging configuration
│
├── src/                               # 🧠 ML PIPELINE (PyTorch Lightning)
│   ├── data/                          # Dataset modules
│   ├── models/                        # Matrix factorization models
│   └── training/                      # Lightning trainers
│
├── tests/
│   ├── unit/                          # Domain + application tests
│   └── integration/                   # API + repository tests
│
├── alembic/                           # Database migrations
├── scripts/                           # Utility scripts
├── data/                              # Raw datasets (gitignored)
├── storage/                           # Model artifacts (gitignored)
└── logs/                              # Application logs (gitignored)
```

---

## 🎭 Experiment State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: create_experiment()

    PENDING --> RUNNING: mark_running()
    PENDING --> FAILED: validation error

    RUNNING --> COMPLETED: mark_completed(metrics)
    RUNNING --> FAILED: mark_failed() / exception

    COMPLETED --> [*]
    FAILED --> [*]

    note right of PENDING
        Initial state when experiment
        is created via API
    end note

    note right of RUNNING
        Training in progress
        Metrics logged per epoch
    end note

    note right of COMPLETED
        Final metrics stored
        Training timeline available
    end note

    note right of FAILED
        Error details captured
        Can retry with new experiment
    end note
```

**State Transitions Enforced in Domain Layer** (`app/core/experiments.py`)

---

## 🗄️ Database Schema

```mermaid
erDiagram
    EXPERIMENTS ||--o{ METRICS : "has many"

    EXPERIMENTS {
        uuid experiment_id PK
        string name
        string experiment_type "centralized/federated"
        string status "pending/running/completed/failed"
        json config "hyperparameters"
        json metrics "final RMSE/MAE"
        timestamp created_at
        timestamp updated_at
    }

    METRICS {
        uuid metric_id PK
        uuid experiment_id FK
        int epoch_or_round
        string metric_name "rmse/mae/loss"
        float metric_value
        timestamp recorded_at
    }
```

**Migrations**: Managed by Alembic (`alembic/versions/`)

---

## 🛣️ API Endpoints Map

```mermaid
graph LR
    subgraph "REST API"
        A[POST /experiments]
        B[GET /experiments/:id]
        C[GET /experiments]
        D[GET /metrics/:experiment_id]
        E[GET /health]
    end

    subgraph "Use Cases"
        F[Create Experiment]
        G[Get Experiment]
        H[List Experiments]
        I[Get Metrics Timeline]
        J[Health Check]
    end

    A --> F
    B --> G
    C --> H
    D --> I
    E --> J

    F --> K[Repository.add]
    G --> L[Repository.get_by_id]
    H --> M[Repository.list]
    I --> N[MetricsRepository.get_by_experiment]

    style A fill:#ffcccc
    style B fill:#ccffcc
    style C fill:#ccffcc
    style D fill:#ccffcc
    style E fill:#ccccff
```

---

## 🔧 Repository Pattern Implementation

```mermaid
classDiagram
    class IExperimentRepository {
        <<interface>>
        +add(experiment)* Experiment
        +get_by_id(id)* Experiment
        +update(experiment)* Experiment
        +list()* List~Experiment~
    }

    class ExperimentRepository {
        -session: AsyncSession
        +add(experiment) Experiment
        +get_by_id(id) Experiment
        +update(experiment) Experiment
        +list() List~Experiment~
        -_to_domain(orm_model) Experiment
        -_to_orm(experiment) ORM_Model
    }

    class ExperimentManager {
        -repository: IExperimentRepository
        +create_experiment(config)
        +run_experiment(id)
        +get_experiment(id)
    }

    IExperimentRepository <|.. ExperimentRepository : implements
    ExperimentManager --> IExperimentRepository : depends on interface

    note for IExperimentRepository "Defined in core/repositories/interfaces.py\n(Domain Layer)"
    note for ExperimentRepository "Implemented in infrastructure/repositories/\n(Infrastructure Layer)"
    note for ExperimentManager "Lives in application/\n(Application Layer)"
```

**Key Insight**: Application layer depends on interface (abstraction), not concrete implementation. Infrastructure can be swapped without touching business logic.

---

## 🤝 Federated Learning Architecture

```mermaid
graph TB
    subgraph "Server (Global)"
        S[Flower Server]
        SM[FedAvgItemsOnly Strategy]
        IG[Global Item Embeddings]
        BG[Global Item Biases]
    end

    subgraph "Client 1"
        C1[Flower Client 1]
        U1[User Embeddings - Local]
        I1[Item Embeddings - Local Copy]
        M1[Matrix Factorization Model]
    end

    subgraph "Client 2"
        C2[Flower Client 2]
        U2[User Embeddings - Local]
        I2[Item Embeddings - Local Copy]
        M2[Matrix Factorization Model]
    end

    subgraph "Client N"
        CN[Flower Client N]
        UN[User Embeddings - Local]
        IN[Item Embeddings - Local Copy]
        MN[Matrix Factorization Model]
    end

    S <-->|Initial Params| C1
    S <-->|Initial Params| C2
    S <-->|Initial Params| CN

    C1 -->|Item Params Only| S
    C2 -->|Item Params Only| S
    CN -->|Item Params Only| S

    S --> SM
    SM --> IG
    SM --> BG

    M1 --> U1
    M1 --> I1
    M2 --> U2
    M2 --> I2
    MN --> UN
    MN --> IN

    style U1 fill:#ffcccc
    style U2 fill:#ffcccc
    style UN fill:#ffcccc
    style IG fill:#ccffcc
    style BG fill:#ccffcc
```

**Privacy-Preserving Approach**:
- ✅ **Item embeddings & biases**: Aggregated globally (FedAvg)
- 🔒 **User embeddings**: Stay local on each client (never shared)

**Implementation**: `app/federated/strategy.py` - Custom `FedAvgItemsOnly` strategy

---

## 🧪 Testing Architecture

```mermaid
graph TB
    subgraph "Unit Tests (tests/unit/)"
        U1[Domain Entities Tests]
        U2[Trainer Tests]
        U3[Calculator Tests]
        U4[State Machine Tests]
    end

    subgraph "Integration Tests (tests/integration/)"
        I1[Repository Tests]
        I2[API Endpoint Tests]
        I3[Database Tests]
    end

    subgraph "Test Infrastructure"
        T1[Test Database]
        T2[Async Fixtures]
        T3[Mock Services]
    end

    U1 --> T3
    U2 --> T3
    U3 -.no external deps.-> U3
    U4 -.no external deps.-> U4

    I1 --> T1
    I1 --> T2
    I2 --> T1
    I2 --> T2
    I3 --> T1

    style U1 fill:#ccffff
    style U2 fill:#ccffff
    style I1 fill:#ffccff
    style I2 fill:#ffccff
```

**Test Strategy**:
- **Unit**: Isolated, fast, no I/O (domain logic, calculators)
- **Integration**: Real database, async operations (repositories, API)

---

## 🔄 Async All The Way

```mermaid
graph LR
    A[FastAPI Endpoint<br/>async def] --> B[Application Service<br/>async def]
    B --> C[Repository<br/>async def]
    C --> D[SQLAlchemy<br/>AsyncSession]
    D --> E[asyncpg<br/>PostgreSQL]

    style A fill:#ff9999
    style B fill:#99ccff
    style C fill:#99ff99
    style D fill:#ffff99
    style E fill:#cc99ff
```

**Async Pattern**: All I/O operations use `async/await` for non-blocking concurrency

---

## 🎓 Key Architectural Patterns

### 1. **Repository Pattern**
- Abstracts data access
- Domain defines interface → Infrastructure implements
- Enables testing with mocks
- **Files**: `core/repositories/interfaces.py` + `infrastructure/repositories/*`

### 2. **Dependency Inversion**
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- **Example**: `ExperimentManager` depends on `IExperimentRepository` (interface), not concrete `ExperimentRepository`

### 3. **Domain-Driven State Machine**
- Business rules enforced in domain entities
- State transitions validated (`PENDING → RUNNING → COMPLETED`)
- **File**: `core/experiments.py`

### 4. **Service Layer Pattern**
- Application services orchestrate domain objects
- Keep controllers thin (API routes just delegate)
- **Files**: `application/experiment_manager.py`, `application/services/*`

### 5. **Strategy Pattern (Federated Learning)**
- Different aggregation strategies (FedAvg, FedProx, etc.)
- Pluggable via Flower framework
- **File**: `federated/strategy.py`

---

## 🚀 Request-to-Response Journey

### Example: Creating a Centralized Experiment

```mermaid
sequenceDiagram
    autonumber

    participant Client
    participant Route as routes/experiments.py
    participant Schema as schemas/ExperimentCreate
    participant Service as ExperimentService
    participant Manager as ExperimentManager
    participant Entity as CentralizedExperiment
    participant Repo as ExperimentRepository
    participant ORM as SQLAlchemy ORM
    participant DB as PostgreSQL

    Client->>Route: POST /experiments<br/>{name, type, config}
    Route->>Schema: Validate request
    Schema-->>Route: Validated data

    Route->>Service: create_experiment(validated_data)
    Service->>Manager: create_and_run(config)

    Manager->>Entity: CentralizedExperiment(config)
    Entity->>Entity: Validate config (__post_init__)
    Entity-->>Manager: Domain entity (PENDING)

    Manager->>Repo: add(entity)
    Repo->>ORM: Convert to ORM model
    ORM->>DB: INSERT INTO experiments
    DB-->>ORM: experiment_id
    ORM-->>Repo: ORM instance
    Repo->>Entity: Convert to domain entity
    Repo-->>Manager: Persisted entity

    Manager->>Entity: mark_running()
    Entity->>Entity: Validate transition
    Entity-->>Manager: State = RUNNING

    Manager->>Repo: update(entity)
    Repo->>DB: UPDATE experiments SET status='RUNNING'

    Manager->>Manager: Start training (async background)
    Manager-->>Service: experiment_id
    Service-->>Route: ExperimentResponse
    Route-->>Client: 201 Created<br/>{experiment_id, status}

    Note over Manager,DB: Training happens asynchronously
```

---

## 📊 Configuration Flow

```mermaid
graph TD
    A[User Input JSON] --> B[Pydantic Schema Validation]
    B --> C{Valid?}
    C -->|No| D[422 Validation Error]
    C -->|Yes| E[Convert to Domain Configuration]
    E --> F[CentralizedConfig / FederatedConfig]
    F --> G{Domain Validation}
    G -->|Invalid| H[ConfigurationError]
    G -->|Valid| I[Create Experiment Entity]
    I --> J[Pass to Trainer]
    J --> K[PyTorch Lightning Module]

    style A fill:#ffcccc
    style E fill:#ccffff
    style F fill:#ccffcc
    style K fill:#ffff99
```

**Two-Layer Validation**:
1. **API Layer**: Pydantic schema validation (types, required fields)
2. **Domain Layer**: Business rule validation (learning_rate > 0, n_factors > 0)

---

## 🔍 Mental Model Checklist

Use this checklist to navigate the codebase:

### "Where do I find...?"

| **What** | **Where** | **Layer** |
|----------|-----------|-----------|
| Business rules & validations | `app/core/experiments.py` | Domain |
| Repository contracts | `app/core/repositories/interfaces.py` | Domain |
| Use case orchestration | `app/application/experiment_manager.py` | Application |
| Training logic | `app/application/training/` | Application |
| Database models (ORM) | `app/infrastructure/models.py` | Infrastructure |
| Repository implementations | `app/infrastructure/repositories/` | Infrastructure |
| API endpoints | `app/api/routes/` | API |
| Request/response schemas | `app/api/schemas/` | API |
| Federated learning setup | `app/federated/` | Application/Infrastructure |
| Matrix factorization models | `src/models/` | ML Pipeline |

### "How do I...?"

| **Task** | **Steps** |
|----------|-----------|
| Add new endpoint | 1. Define route in `api/routes/` <br/> 2. Create Pydantic schemas <br/> 3. Wire to service in dependencies |
| Add new experiment type | 1. Create entity in `core/experiments.py` <br/> 2. Add config in `core/configuration.py` <br/> 3. Implement trainer in `application/training/` |
| Change database schema | 1. Modify ORM models in `infrastructure/models.py` <br/> 2. Run `alembic revision --autogenerate` <br/> 3. Review migration, apply with `alembic upgrade head` |
| Add business validation | Modify domain entity's `__post_init__` in `core/` |
| Add new metric | 1. Add to `core/metrics.py` <br/> 2. Update calculator in `application/reporting/` <br/> 3. Persist via `MetricsRepository` |

---

## 🎯 Core Design Principles in Action

### SOLID Principles

1. **Single Responsibility**: Each module has one reason to change
   - `CentralizedTrainer`: Only trains centralized models
   - `MetricsLogger`: Only logs metrics
   - `ExperimentRepository`: Only persists experiments

2. **Open-Closed**: Extend without modifying
   - New experiment types: Subclass `Experiment` base
   - New aggregation strategies: Implement Flower strategy interface

3. **Liskov Substitution**: Subtypes are substitutable
   - `CentralizedExperiment` and `FederatedExperiment` can replace `Experiment`

4. **Interface Segregation**: Small, focused interfaces
   - `IExperimentRepository` vs `IMetricsRepository` (separate concerns)

5. **Dependency Inversion**: Depend on abstractions
   - `ExperimentManager` → `IExperimentRepository` (interface)
   - **NOT** → `ExperimentRepository` (concrete implementation)

### Other Principles

- **KISS**: Simple solutions (e.g., JSON config storage vs complex schema)
- **YAGNI**: No over-engineering (only implemented features: centralized + federated experiments)
- **DRY**: `BaseRepository` for shared CRUD operations

---

## 🧭 Navigation Tips

### Starting Points by Task

**Understanding the flow**:
1. Start: `app/api/main.py` (entry point)
2. Follow: `app/api/routes/experiments.py` → `app/application/services/` → `app/application/experiment_manager.py`
3. Deep dive: `app/core/experiments.py` (domain rules)

**Adding a feature**:
1. Domain: Define entity/interface in `app/core/`
2. Application: Implement use case in `app/application/`
3. Infrastructure: Add persistence in `app/infrastructure/`
4. API: Expose via `app/api/routes/`

**Debugging issues**:
1. API errors: Check `app/api/routes/` + `app/api/schemas/`
2. Business logic errors: Check `app/core/` + `app/application/`
3. Database errors: Check `app/infrastructure/models.py` + `alembic/versions/`
4. Training errors: Check `app/application/training/` + `src/models/`

**Understanding federated learning**:
1. Partitioning: `app/federated/partitioner.py`
2. Aggregation: `app/federated/strategy.py`
3. Client/Server: `app/federated/client_app.py` + `server_app.py`
4. Integration: `app/application/training/federated_simulation_manager.py`

---

## 🔗 Cross-References

This canvas connects to:

- **CLAUDE.md**: Development commands, architecture overview, common gotchas
- **Module READMEs**:
  - `src/data/README.md`: Dataset preprocessing details
  - `src/models/README.md`: Matrix factorization implementation
- **Code Comments**: Inline documentation in critical modules
- **Alembic Migrations**: `alembic/versions/` - Database evolution history

---

## 📝 Quick Commands Reference

```bash
# Run app
uv run uvicorn app.api.main:app --reload

# Create migration after schema change
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Run tests
uv run pytest                           # All tests
uv run pytest tests/unit/               # Unit only
uv run pytest --cov=app                 # With coverage

# Code quality
uv run black app tests                  # Format
uv run ruff check app tests             # Lint
uv run mypy app                         # Type check
```

---

## 🎨 Visual Legend

```mermaid
graph LR
    A[Domain Layer]
    B[Application Layer]
    C[Infrastructure Layer]
    D[API Layer]
    E[External System]

    style A fill:#ff9999
    style B fill:#99ccff
    style C fill:#99ff99
    style D fill:#ffff99
    style E fill:#cc99ff
```

- 🔴 **Domain**: Business rules, entities, interfaces
- 🔵 **Application**: Use cases, orchestration, services
- 🟢 **Infrastructure**: Database, external adapters
- 🟡 **API**: HTTP routes, schemas, presentation
- 🟣 **External**: Third-party systems, databases

---

## 🧠 Maintaining Your Mental Model

**When reading code, ask**:
1. **Which layer am I in?** (Domain/Application/Infrastructure/API)
2. **What's this component's single responsibility?**
3. **What does it depend on?** (Always check imports - are they from outer layers?)
4. **What's the data flow?** (Request → Domain → Persistence → Response)

**When making changes**:
1. **Start in Domain**: Does this change business rules? Update entities/configs first
2. **Update Application**: Does orchestration logic change? Update managers/trainers
3. **Persist in Infrastructure**: Does data model change? Update ORM + migration
4. **Expose in API**: Should users access this? Add route + schema

**Remember**: Dependencies flow INWARD (API → Application → Domain), never outward!

---

*Last Updated: 2026-01-22*
*Generated for: QuiteReads Dashboard FYP Project*
