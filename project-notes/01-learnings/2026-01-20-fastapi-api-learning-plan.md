# FastAPI & Backend Learning Plan
> A structured path to deeply understand the `app/api` folder before moving to the ML pipeline

---

## Phase 1: Prerequisites (Foundational Concepts)

Before diving into the code, ensure you understand these concepts:

### 1.1 Python Fundamentals
- [ ] **Async/Await** - Understanding `async def` and `await` keywords
- [ ] **Type Hints** - Function annotations like `def foo(x: int) -> str`
- [ ] **Decorators** - How `@decorator` syntax works
- [ ] **Context Managers** - The `with` statement and `__enter__`/`__exit__`

### 1.2 Web API Fundamentals
- [ ] **HTTP Methods** - GET, POST, PUT, DELETE and when to use each
- [ ] **HTTP Status Codes** - 200, 201, 204, 400, 404, 422, 500
- [ ] **REST Principles** - Resource-based URLs, statelessness
- [ ] **Request/Response Cycle** - Headers, body, query params, path params

### 1.3 Design Patterns
- [ ] **Dependency Injection** - Passing dependencies rather than creating them
- [ ] **Repository Pattern** - Abstracting data access
- [ ] **Service Layer** - Business logic orchestration
- [ ] **DTO (Data Transfer Object)** - Separating API models from domain models

---

## Phase 2: FastAPI Core Concepts

Study these FastAPI-specific concepts (read docs or tutorials):

### 2.1 FastAPI Basics
| Concept | What to Learn |
|---------|---------------|
| `FastAPI()` | App initialization and configuration |
| `APIRouter` | Grouping related endpoints |
| `@app.get()`, `@app.post()` | Route decorators and HTTP methods |
| Path Parameters | `/items/{item_id}` syntax |
| Query Parameters | `?status=active&limit=10` |
| Request Body | Receiving JSON payloads |

### 2.2 Pydantic Models
| Concept | What to Learn |
|---------|---------------|
| `BaseModel` | Creating data models |
| `Field()` | Adding validation, descriptions, examples |
| Validation | Automatic request validation |
| Serialization | Converting models to JSON (`.dict()`, `.json()`) |
| `from_orm()` | Converting ORM objects to Pydantic models |

### 2.3 Dependency Injection
| Concept | What to Learn |
|---------|---------------|
| `Depends()` | Declaring dependencies in route functions |
| Dependency Functions | Creating reusable dependencies |
| Yield Dependencies | Dependencies with setup/teardown |

### 2.4 Error Handling
| Concept | What to Learn |
|---------|---------------|
| `HTTPException` | Raising HTTP errors with status codes |
| Exception Handlers | `@app.exception_handler()` for custom exceptions |

---

## Phase 3: Reading the Code (Recommended Order)

Read the files in this specific order to build understanding progressively:

### Step 1: Schemas (Data Contracts) ⏱️ ~30 min
> **Goal:** Understand what data flows in and out of the API

```
📁 app/api/schemas/
```

| Order | File | Focus Areas |
|-------|------|-------------|
| 1a | [experiment_schemas.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/schemas/experiment_schemas.py) | Enums, request models, response models, Field validation |
| 1b | [metrics_schemas.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/schemas/metrics_schemas.py) | Simpler schemas, batch requests, analytics responses |

**Questions to Answer:**
- [ ] What's the difference between a Request schema and a Response schema?
- [ ] How does `Field()` add validation rules?
- [ ] Why are there separate Create/Complete/Response schemas?
- [ ] What does `from_orm=True` in Config enable?

---

### Step 2: Dependencies (Wiring) ⏱️ ~15 min
> **Goal:** Understand how services are created and injected

```
📄 app/api/dependencies.py
```

| Order | File | Focus Areas |
|-------|------|-------------|
| 2 | [dependencies.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/dependencies.py) | Factory functions, repository creation, service wiring |

**Questions to Answer:**
- [ ] What does `get_experiment_service()` return?
- [ ] Where does the `db` session come from?
- [ ] Why do we create repositories inside the dependency function?

---

### Step 3: Routes (Endpoints) ⏱️ ~45 min
> **Goal:** Understand how HTTP requests are handled

```
📁 app/api/routes/
```

| Order | File | Focus Areas |
|-------|------|-------------|
| 3a | [health.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/routes/health.py) | Simplest possible endpoint (start here!) |
| 3b | [experiments.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/routes/experiments.py) | Full CRUD, status codes, `Depends()`, error handling |
| 3c | [metrics.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/routes/metrics.py) | Nested routes, batch operations, query filters |

**Questions to Answer:**
- [ ] How does `Depends(get_session)` work?
- [ ] What's the flow: HTTP Request → Route → Service → Repository?
- [ ] How are exceptions converted to HTTP status codes?
- [ ] What does `response_model=ExperimentResponse` do?

---

### Step 4: Main Application (Glue) ⏱️ ~20 min
> **Goal:** Understand how everything connects together

```
📄 app/api/main.py
```

| Order | File | Focus Areas |
|-------|------|-------------|
| 4 | [main.py](file:///c:/Users/Asus/Documents/MMU/BCS/FYP/FYP2/fedrec-dashboard/app/api/main.py) | App init, middleware, exception handlers, router registration |

**Questions to Answer:**
- [ ] What does `app.include_router()` do?
- [ ] How do global exception handlers work?
- [ ] What is CORS and why is it configured?

---

## Phase 4: Hands-On Practice

### 4.1 Run the API
```powershell
uvicorn app.api.main:app --reload
```

### 4.2 Explore Interactive Docs
- Open `http://localhost:8000/docs` (Swagger UI)
- Try each endpoint manually
- Observe request/response formats

### 4.3 Mini Exercises
- [ ] Create a centralized experiment via the API
- [ ] List experiments with different filters
- [ ] Add metrics to an experiment
- [ ] Intentionally trigger a 404 error
- [ ] Intentionally trigger a 422 validation error

---

## Phase 5: Deep Understanding Checklist

Complete these to confirm solid understanding:

### Architecture Understanding
- [ ] I can draw the data flow from HTTP request to database and back
- [ ] I understand why schemas are separate from domain models
- [ ] I understand the role of each layer (routes, services, repositories)

### Code Understanding  
- [ ] I can explain every line in `main.py`
- [ ] I can add a new endpoint to an existing router
- [ ] I can create a new Pydantic schema with validation
- [ ] I can add a new route file and register it

### Pattern Recognition
- [ ] I recognize Dependency Injection in action
- [ ] I understand the Repository pattern usage
- [ ] I see how DTOs protect internal domain models

---

## Recommended External Resources

| Topic | Resource |
|-------|----------|
| FastAPI Official Tutorial | https://fastapi.tiangolo.com/tutorial/ |
| Pydantic V2 Docs | https://docs.pydantic.dev/latest/ |
| HTTP Status Codes | https://httpstatuses.io/ |
| REST API Design | https://restfulapi.net/ |

---

## Summary: Reading Order Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: Prerequisites                       │
│              (Python async, HTTP, Design Patterns)              │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 2: FastAPI Concepts                      │
│            (Read docs: routing, Pydantic, Depends)              │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: Read Code                           │
│                                                                 │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐       │
│   │  SCHEMAS    │ -> │ DEPENDENCIES │ -> │   ROUTES    │       │
│   │ (1a, 1b)    │    │     (2)      │    │ (3a,3b,3c)  │       │
│   └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                 │               │
│                                                 ▼               │
│                                          ┌──────────┐           │
│                                          │  MAIN    │           │
│                                          │   (4)    │           │
│                                          └──────────┘           │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 4: Hands-On Practice                    │
│           (Run API, use Swagger, try endpoints)                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 5: Confirm Understanding                  │
│                    (Complete checklists)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

> **Estimated Total Time:** 4-6 hours of focused study

After completing this plan, you'll be ready to move to the **Core ML Pipeline** with a solid foundation in how the API layer works!
