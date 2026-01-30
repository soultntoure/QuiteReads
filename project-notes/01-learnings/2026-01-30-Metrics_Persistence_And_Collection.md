# Metrics Persistence And Collection

## Production Code Path

### Persistence Flow

1. **experiment_manager.py:138** — After training completes, calls `_persist_training_metrics`
2. **experiment_manager.py:160-221** — `_persist_training_metrics` extracts loss/rmse/mae from the `MetricsLogger` and builds `PerformanceMetric` domain objects
3. **experiment_manager.py:215** — Calls `metrics_service.add_metrics_batch()` which writes them to PostgreSQL

### Collection During Training

1. **centralized_trainer.py:175-221** — `MetricsLoggingCallback` hooks into Lightning's epoch-end events and writes loss/rmse/mae to the in-memory `MetricsLogger`
2. **centralized_trainer.py:343** — `MetricsLogger` is created fresh at training start
3. After `trainer.fit()` finishes, `MetricsLogger` holds all per-epoch data, which `ExperimentManager` then persists

## Verification Tests

The following tests verify the metrics persistence pipeline:

- **test_centralized_pipeline.py:146-189** — Trains with real DB, queries metrics back, asserts exact count (6), all 3 types (loss, rmse, mae), valid values
- **test_centralized_pipeline.py:270-311** — Trains 3 epochs, retrieves, verifies contiguous epoch ordering

## Manual Verification

### Step 1: Create an Experiment

```bash
curl -X POST http://localhost:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{"name": "Manual Test", "experiment_type": "centralized", "config": {"n_factors": 8, "n_epochs": 3, "learning_rate": 0.01}}'
```

Note the `experiment_id` from the response.

### Step 2: Query Metrics via API

```bash
curl http://localhost:8000/metrics/<experiment_id>
```

### Step 3: Query Metrics Directly from PostgreSQL

```sql
-- Check experiments
SELECT experiment_id, name, status, metrics FROM experiments;

-- Check per-epoch metrics for a specific experiment
SELECT name, round_number, value, context
FROM metrics
WHERE experiment_id = '<id>'
ORDER BY name, round_number;
```

### Expected Output

You should see rows like:

| name | round_number | value | context    |
|------|--------------|-------|------------|
| loss | 0            | 1.32  | training   |
| loss | 1            | 0.89  | training   |
| loss | 2            | 0.71  | training   |
| rmse | 0            | 1.14  | validation |
| rmse | 1            | 0.94  | validation |
| rmse | 2            | 0.85  | validation |
| mae  | 0            | 0.99  | validation |
| mae  | 1            | 0.78  | validation |
| mae  | 2            | 0.68  | validation |
