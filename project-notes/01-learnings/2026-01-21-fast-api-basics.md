
## FastAPI App & Routing (Core, Not Syntax)

![FastAPI Routing Core](../images/fastapi_routing_core.png)
### The non-negotiable idea

FastAPI is **not** “a file with endpoints”.

It is:

> **A request router + dependency resolver + schema enforcer**

If you don’t structure routing correctly now, everything later (services, DB, auth, AI pipelines) becomes messy.

---

## `FastAPI()` — What the app *actually* is

Think of `FastAPI()` as:

* A **registry** of routes
* A **dependency graph manager**
* An **OpenAPI schema generator**

It is *not* where business logic lives.

Typical minimal app:

```python
app = FastAPI(
    title="Experiment Service",
    version="1.0.0"
)
```

Config here is **global**:

* Middleware
* Exception handlers
* Routers
* Lifespan events

---

## 2.1.2 `APIRouter` — Why this exists (this matters)

`APIRouter` is **not optional structure polish**.
It is how you **scale without pain**.

Think in terms of **bounded contexts**:

* experiments
* users
* metrics
* auth

Each gets:

* Its own router
* Its own dependencies
* Its own prefix + tags

Example mental model (no need to code yet):

```
app
 ├── experiments router
 │     ├── POST /experiments
 │     ├── GET  /experiments/{id}
 │
 ├── metrics router
 │     ├── GET /metrics
```

**Rule you must internalize**:

> The app includes routers. Routers define routes. Routes call services.

Never skip levels.

---

## 2.1.3 Route decorators — What they *really* do

When you write:

```python
@router.post("/experiments")
```

You are declaring:

* HTTP method constraint
* Path matching rule
* Schema contract (inputs + outputs)
* Dependency injection entry point

You are **not** “writing a function that runs on request”
You are **registering metadata**.

This explains:

* Why decorators run at import time
* Why wrong imports break the app
* Why circular imports are deadly

---

## 2.1.4 Path vs Query Parameters (boundary clarity)

### Path parameters

```text
/experiments/{experiment_id}
```

They:

* Identify *a specific resource*
* Are **required**
* Define *what* you’re operating on

### Query parameters

```text
/experiments?status=active&limit=10
```

They:

* Modify *how* you view the resource
* Are optional by default
* Never change identity

**Golden rule**:

> If removing it changes *which* thing you mean → path
> If removing it changes *how* you view it → query

![Path vs Query Parameters](../images/path_vs_query_parameters.png)
---

## Quick checkpoint (one question)

You see this endpoint:

```
GET /experiments/123?version=2
```

**Question:**
Which part identifies the resource, and which part modifies the request behavior?

**Answer:**
The path /experiments/123 identifies the resource, while the query parameter version=2 modifies the request behavior