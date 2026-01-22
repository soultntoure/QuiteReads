# Reporting Module

## Overview
The reporting module provides metrics calculation and logging capabilities for evaluating recommendation system performance during training. It computes RMSE and MAE metrics and captures per-epoch/round convergence data for both centralized and federated experiments.

## Purpose
- Compute evaluation metrics (RMSE, MAE) for recommendation quality assessment
- Log per-epoch training and validation metrics for convergence analysis
- Provide a consistent metrics format for comparison between centralized and federated approaches

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `metrics_calculator.py` | Computes RMSE and MAE evaluation metrics | Supports both PyTorch tensors and Python sequences |
| `metrics_logger.py` | Captures per-epoch metrics during training | Dataclass-based logger compatible with federated history format |
| `export_manager.py` | (Placeholder) Future metrics export functionality | Currently empty |
| `__init__.py` | Module exports | Exposes calculator functions and MetricsLogger class |

---

## 1. metrics_calculator.py

### Overview
Provides pure functions for computing recommendation system evaluation metrics. Supports flexible input types (PyTorch tensors or Python sequences) and validates inputs before computation. All metrics compare predicted ratings against actual ratings from test sets.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `compute_rmse()` | Computes Root Mean Squared Error | Returns float, emphasizes larger errors |
| `compute_mae()` | Computes Mean Absolute Error | Returns float, linear error magnitude |
| `compute_metrics()` | Computes both RMSE and MAE in one pass | Returns dict with both metrics, more efficient |
| `_to_tensor()` | Converts inputs to PyTorch tensors | Private helper, handles type normalization |
| `_validate_inputs()` | Validates tensor shapes and non-emptiness | Private helper, raises ValueError on invalid inputs |

### Usage Examples

```python
from app.application.reporting import compute_rmse, compute_mae, compute_metrics
import torch

# Using PyTorch tensors
predictions = torch.tensor([4.5, 3.2, 4.8, 2.1])
actuals = torch.tensor([5.0, 3.0, 4.5, 2.5])

# Compute individual metrics
rmse = compute_rmse(predictions, actuals)
# Returns: 0.387 (emphasizes the 0.5 error more)

mae = compute_mae(predictions, actuals)
# Returns: 0.3 (average absolute deviation)

# Compute both metrics efficiently
metrics = compute_metrics(predictions, actuals)
# Returns: {"rmse": 0.387, "mae": 0.3}

# Using Python lists (automatically converted)
pred_list = [4.5, 3.2, 4.8, 2.1]
actual_list = [5.0, 3.0, 4.5, 2.5]
metrics = compute_metrics(pred_list, actual_list)

# Validation errors
try:
    compute_rmse([1.0, 2.0], [1.0])  # Mismatched lengths
except ValueError as e:
    print(e)  # "Shape mismatch: predictions torch.Size([2]) vs actuals torch.Size([1])"

try:
    compute_mae([], [])  # Empty inputs
except ValueError as e:
    print(e)  # "Inputs cannot be empty"
```

### Significance
This module follows the **Single Responsibility Principle** by providing focused metric computation separate from logging or persistence. The flexible input types (tensors or sequences) make it reusable across different training frameworks (PyTorch Lightning, raw PyTorch, scikit-surprise). Input validation ensures robustness and clear error messages. The `compute_metrics()` function demonstrates **DRY** by computing both metrics in a single tensor pass, improving efficiency for large datasets.

---

## 2. metrics_logger.py

### Overview
Provides a stateful logger for capturing training and validation metrics across epochs or federated rounds. Uses a dataclass structure compatible with the federated learning history format, enabling direct comparison between centralized and federated convergence in visualization dashboards.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `MetricsLogger` (class) | Captures and retrieves per-epoch metrics | Dataclass with nested dict structure |
| `log_training()` | Records training loss for an epoch | Stores in `history["training"][epoch]` |
| `log_validation()` | Records validation RMSE and MAE | Stores in `history["validation"][epoch]` |
| `get_training_losses()` | Retrieves all training losses in order | Returns sorted list by epoch |
| `get_validation_rmse()` | Retrieves all validation RMSE values | Returns sorted list by epoch |
| `get_validation_mae()` | Retrieves all validation MAE values | Returns sorted list, handles None |
| `get_final_metrics()` | Gets last epoch's validation metrics | Returns dict with final RMSE/MAE |
| `reset()` | Clears all logged metrics | Resets history to empty state |
| `num_epochs` (property) | Counts total epochs logged | Union of training and validation epochs |

### Usage Examples

```python
from app.application.reporting import MetricsLogger, compute_metrics
import torch

# Initialize logger
logger = MetricsLogger()

# Simulate training loop
for epoch in range(5):
    # Training phase
    train_loss = 0.85 - (epoch * 0.1)  # Mock decreasing loss
    logger.log_training(epoch, train_loss)

    # Validation phase
    val_preds = torch.randn(100) + 3.5
    val_actuals = torch.randn(100) + 3.5
    metrics = compute_metrics(val_preds, val_actuals)
    logger.log_validation(
        epoch,
        rmse=metrics["rmse"],
        mae=metrics["mae"]
    )

# Retrieve convergence data
train_losses = logger.get_training_losses()
# Returns: [0.85, 0.75, 0.65, 0.55, 0.45]

val_rmse = logger.get_validation_rmse()
# Returns: [rmse_0, rmse_1, rmse_2, rmse_3, rmse_4]

# Get final performance
final = logger.get_final_metrics()
# Returns: {"rmse": rmse_4, "mae": mae_4}

# Check total epochs
print(logger.num_epochs)  # Returns: 5

# Access raw history (for persistence)
history_dict = logger.history
# Structure: {
#   "training": {"0": {"loss": 0.85}, "1": {...}, ...},
#   "validation": {"0": {"rmse": ..., "mae": ...}, ...}
# }

# Reset for new experiment
logger.reset()
assert logger.num_epochs == 0
```

### Significance
The `MetricsLogger` follows **Open-Closed Principle** by allowing extension (adding new metric types) without modifying the core structure. The nested dictionary format mirrors the federated learning history returned by Flower framework, enabling **seamless comparison** between centralized and federated convergence plots in the dashboard. String-keyed epochs support federated round numbers that may not be sequential. The dataclass design with default factory ensures immutability and thread-safety for concurrent experiments.

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Application layer (orchestration and business logic) |
| **Design Patterns** | Pure functions (calculator), stateful dataclass (logger) |
| **SOLID Adherence** | Single Responsibility (separate calculation from logging), Dependency Inversion (no coupling to persistence) |
| **Reusability** | Calculator functions accept multiple input types, logger format aligns with Flower framework |
| **Testing** | Pure functions enable easy unit testing, logger's dict structure simplifies assertion |
| **Integration** | Used by `centralized_trainer.py` and `federated_simulation_manager.py` for consistent metrics |
| **Future Extension** | `export_manager.py` placeholder for CSV/JSON export, metrics repository for persistence |
