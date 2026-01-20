
## Without the Type Alias

If you **didn't** have this line:
```python
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]
```

You'd have to write **every single route** like this:

```python
@router.post("/centralized", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_centralized_experiment(
    request: CreateCentralizedExperimentRequest,
    service: ExperimentService = Depends(get_experiment_service),  # ← REPEATED
):
    ...

@router.post("/federated", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_federated_experiment(
    request: CreateFederatedExperimentRequest,
    service: ExperimentService = Depends(get_experiment_service),  # ← REPEATED
):
    ...

@router.get("/", response_model=ExperimentListResponse)
async def list_experiments(
    service: ExperimentService = Depends(get_experiment_service),  # ← REPEATED
    status_filter: ExperimentStatus | None = Query(default=None),
    type_filter: ExperimentType | None = Query(default=None),
):
    ...

@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    service: ExperimentService = Depends(get_experiment_service),  # ← REPEATED
):
    ...
```

Notice the problem? **You're repeating the same thing 10+ times!**

---

## With the Type Alias

```python
# Define ONCE at the top
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]

# Use everywhere
@router.post("/centralized", ...)
async def create_centralized_experiment(
    request: CreateCentralizedExperimentRequest,
    service: ExperimentServiceDep,  # ← Clean!
):
    ...

@router.post("/federated", ...)
async def create_federated_experiment(
    request: CreateFederatedExperimentRequest,
    service: ExperimentServiceDep,  # ← Clean!
):
    ...
```

**Now you write it once, use it everywhere.**

---

## What `Annotated` Does

`Annotated` is a Python feature that lets you **attach metadata to a type**.

### Basic Python Type Annotation:
```python
service: ExperimentService
```
**Meaning:** "service is of type ExperimentService"

### With Annotated:
```python
service: Annotated[ExperimentService, Depends(get_experiment_service)]
```
**Meaning:** 
- "service is of type ExperimentService" 
- **PLUS** "FastAPI, here's extra info: get it by calling `get_experiment_service()`"

---

## Breaking Down the Parts

```python
Annotated[ExperimentService, Depends(get_experiment_service)]
         ↑                    ↑
         |                    |
    Actual type         Metadata (FastAPI reads this)
```

### 1. `ExperimentService` (the type)
- Type checkers (mypy, pyright) see this
- Your IDE knows `service` has methods like `.create_centralized_experiment()`
- This part is for **static analysis**

### 2. `Depends(get_experiment_service)` (the metadata)
- FastAPI reads this at **runtime**
- Tells FastAPI: "Before calling this function, execute `get_experiment_service()` and pass the result as `service`"
- This part is for **dependency injection**

---

## Visual Comparison

### Old Way (Before Type Alias):
```python
async def create_experiment(
    request: CreateExperimentRequest,
    service: ExperimentService = Depends(get_experiment_service),
    #        ↑ Type for IDE      ↑ Default value for FastAPI
):
    ...
```

**Problem:** You're mixing two concerns:
1. Type annotation (`ExperimentService`) for your IDE
2. Dependency instruction (`Depends(...)`) for FastAPI

And you repeat it everywhere!

### New Way (With Type Alias):
```python
# Define once
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]

# Use everywhere
async def create_experiment(
    request: CreateExperimentRequest,
    service: ExperimentServiceDep,
    #        ↑ Everything bundled together
):
    ...
```

**Benefits:**
1. Write it once
2. Change it once (if you switch dependency injection logic)
3. Cleaner function signatures

---

## What Happens at Runtime?

When FastAPI sees:
```python
service: ExperimentServiceDep
```

It does this:

1. **Reads the metadata** from `Annotated`
2. **Finds** `Depends(get_experiment_service)`
3. **Calls** `get_experiment_service()` 
4. **Injects** the result into `service` parameter

---

## Real-World Analogy

Think of it like a recipe card:

### Without Type Alias:
Every time you cook, you write out the full recipe:
```
Ingredient: Tomato Sauce
How to get it: Go to store → Aisle 3 → Grab can → Open it
```

You write this 10 times for 10 dishes.

### With Type Alias:
```python
# Define once
TomatoSauce = "Already prepared sauce from pantry"

# Use everywhere
Pizza needs: TomatoSauce
Pasta needs: TomatoSauce
Soup needs: TomatoSauce
```

---

## What If You Had Multiple Services?

Without type aliases:
```python
async def create_experiment(
    request: CreateExperimentRequest,
    exp_service: ExperimentService = Depends(get_experiment_service),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    ...
```

With type aliases:
```python
# Define once
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
DBSessionDep = Annotated[Session, Depends(get_db)]

# Use everywhere
async def create_experiment(
    request: CreateExperimentRequest,
    exp_service: ExperimentServiceDep,
    user_service: UserServiceDep,
    auth_service: AuthServiceDep,
    db: DBSessionDep,
):
    ...
```

Much cleaner!

---

## The Key Insight

**Type aliases don't change behavior—they just make code DRY (Don't Repeat Yourself).**

These two are **functionally identical**:

```python
# Option A: Direct annotation
service: ExperimentService = Depends(get_experiment_service)

# Option B: Type alias
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]
service: ExperimentServiceDep
```

Both produce the exact same runtime behavior. The type alias is just **convenience + maintainability**.

---

## Quick Test

**Question:** If you change the dependency injection logic (e.g., switch from `get_experiment_service` to `get_cached_experiment_service`), where do you make the change?

**Without type alias:** Change it in **every single route function** (10+ places)

**With type alias:** Change it **once** in the type alias definition:
```python
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_cached_experiment_service)]
                                                              ↑ Changed here, affects everywhere
```

---

**Does this clarify it?** The type alias is purely a developer experience improvement—it doesn't add new capabilities, just reduces repetition.