"""Metrics calculation functions for recommendation system evaluation.

Provides RMSE and MAE computation for comparing predicted vs actual ratings.
"""

import math
from typing import Sequence, Union

import torch


def compute_rmse(predictions: Union[torch.Tensor, Sequence[float]], actuals: Union[torch.Tensor, Sequence[float]]) -> float:
    """Compute Root Mean Squared Error between predictions and actuals.

    Args:
        predictions: Predicted rating values.
        actuals: Actual rating values.

    Returns:
        RMSE value as a float.

    Raises:
        ValueError: If inputs are empty or have mismatched lengths.
    """
    predictions = _to_tensor(predictions)
    actuals = _to_tensor(actuals)

    _validate_inputs(predictions, actuals)

    with torch.no_grad():
        mse = torch.mean((predictions - actuals) ** 2)
    return math.sqrt(float(mse))


def compute_mae(predictions: Union[torch.Tensor, Sequence[float]], actuals: Union[torch.Tensor, Sequence[float]]) -> float:
    """Compute Mean Absolute Error between predictions and actuals.

    Args:
        predictions: Predicted rating values.
        actuals: Actual rating values.

    Returns:
        MAE value as a float.

    Raises:
        ValueError: If inputs are empty or have mismatched lengths.
    """
    predictions = _to_tensor(predictions)
    actuals = _to_tensor(actuals)

    _validate_inputs(predictions, actuals)

    with torch.no_grad():
        mae = torch.mean(torch.abs(predictions - actuals))
    return float(mae)


def compute_metrics(predictions: Union[torch.Tensor, Sequence[float]], actuals: Union[torch.Tensor, Sequence[float]]) -> dict[str, float]:
    """Compute both RMSE and MAE.

    Args:
        predictions: Predicted rating values.
        actuals: Actual rating values.

    Returns:
        Dictionary with 'rmse' and 'mae' keys.

    Raises:
        ValueError: If inputs are empty or have mismatched lengths.
    """
    return {
        "rmse": compute_rmse(predictions, actuals),
        "mae": compute_mae(predictions, actuals),
    }


def _to_tensor(values: Union[torch.Tensor, Sequence[float]]) -> torch.Tensor:
    """Convert input to tensor if not already.

    Args:
        values: Input values as tensor or sequence.

    Returns:
        PyTorch tensor (detached from gradients).
    """
    if isinstance(values, torch.Tensor):
        return values.detach().float()
    return torch.tensor(values, dtype=torch.float32)


def _validate_inputs(predictions: torch.Tensor, actuals: torch.Tensor) -> None:
    """Validate prediction and actual tensors.

    Args:
        predictions: Predicted values tensor.
        actuals: Actual values tensor.

    Raises:
        ValueError: If inputs are empty, have mismatched lengths, or contain NaN/Inf.
    """
    if predictions.numel() == 0 or actuals.numel() == 0:
        raise ValueError("Inputs cannot be empty")

    if predictions.shape != actuals.shape:
        raise ValueError(
            f"Shape mismatch: predictions {predictions.shape} vs actuals {actuals.shape}"
        )

    if torch.isnan(predictions).any() or torch.isinf(predictions).any():
        raise ValueError("Predictions contain NaN or Inf values")

    if torch.isnan(actuals).any() or torch.isinf(actuals).any():
        raise ValueError("Actuals contain NaN or Inf values")
