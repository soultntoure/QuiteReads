# Pydantic Schema Examples Need to be Lists, Not Dicts

**Date:** 2026-01-21  
**Category:** API Schema / Pydantic Validation  
**Impact:** Server wouldn't start at all

## What Happened

So I was spinning up the FastAPI server with `uvicorn app.api.main:app --reload` and got hit with a wall of Pydantic validation errors. The server just refused to start, throwing 14 validation errors about the OpenAPI schema.

At first glance, it looked super confusing - something about `components.schemas.*.examples` needing to be a list but getting a dict instead. The stack trace mentioned all my schema models: `ConfigurationSchema`, `CreateCentralizedExperimentRequest`, `CreateFederatedExperimentRequest`, `CompleteExperimentRequest`, `ExperimentMetricsSchema`, `ExperimentResponse`, and `ExperimentListResponse`.

## The Mistake

In my Pydantic v2 schemas, I had defined the `json_schema_extra` examples like this:

```python
class ConfigurationSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {  # ❌ This is WRONG - it's a dict!
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        }
    )
```

Turns out that's not the right format! OpenAPI 3.1 (which Pydantic v2 uses) requires `examples` to be a **list of example objects**, not a single object.

## The Fix

Super simple once I knew what to look for - just wrap each example in a list:

```python
class ConfigurationSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [  # ✅ Now it's a list!
                {
                    "learning_rate": 0.01,
                    "batch_size": 32,
                    "epochs": 10,
                    "model_type": "biased_svd"
                }
            ]
        }
    )
```

Had to do this for all 7 schema models that had examples defined. After saving, the server auto-reloaded and boom - started up perfectly with no errors.

## Why This Happened

I probably copied this pattern from an older Pydantic v1 example or just assumed it would work like that. The OpenAPI 3.1 spec is stricter about the format, and Pydantic v2 enforces this properly.

## Lesson Learned

- **Always check the Pydantic v2 docs** when using `json_schema_extra` - the format changed from v1
- The `examples` field in OpenAPI 3.1 is **always a list**, even if you only have one example
- When you get Pydantic validation errors on server startup, read them carefully - they usually tell you exactly what's wrong (in this case: "Input should be a valid list")
- The error stack trace will point to all the affected schema models, so you can fix them all at once

## Files Changed

- `app/api/schemas/experiment_schemas.py` - Updated all 7 schema models to wrap examples in lists

## Commit

```
fix(api): wrap Pydantic schema examples in lists

OpenAPI 3.1 requires the 'examples' field in json_schema_extra to be
a list of example objects, not a single object. This was causing
Pydantic validation errors on server startup.
```

## References

- [Pydantic v2 JSON Schema Docs](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [OpenAPI 3.1 Specification - Example Object](https://spec.openapis.org/oas/v3.1.0#example-object)
