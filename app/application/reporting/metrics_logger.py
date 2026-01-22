"""Metrics logger for capturing per-epoch training metrics.

Adapted from EpochMetricsCallback for manual PyTorch training loops.
Stores metrics in a format compatible with federated training history
for convergence plot comparison.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricsLogger:
    """Captures per-epoch metrics during training for convergence analysis.

    Stores validation and training metrics in a dictionary format compatible
    with the federated training history structure, enabling direct comparison
    in convergence plots.

    Attributes:
        history: Dict with 'validation' and 'training' sub-dicts, keyed by epoch.
    """

    history: dict = field(default_factory=lambda: {"validation": {}, "training": {}})

    def log_training(self, epoch: int, loss: float) -> None:
        """Log training metrics for an epoch.

        Args:
            epoch: Current epoch number (0-indexed).
            loss: Training loss value.
        """
        self.history["training"][str(epoch)] = {"loss": loss}

    def log_validation(
        self,
        epoch: int,
        rmse: float,
        mae: Optional[float] = None,
    ) -> None:
        """Log validation metrics for an epoch.

        Args:
            epoch: Current epoch number (0-indexed).
            rmse: Validation RMSE value.
            mae: Validation MAE value (optional).
        """
        self.history["validation"][str(epoch)] = {
            "rmse": rmse,
            "mae": mae,
        }

    def get_training_losses(self) -> list[float]:
        """Get all training losses in epoch order.

        Returns:
            List of training loss values ordered by epoch.
        """
        if not self.history["training"]:
            return []

        epochs = sorted(int(e) for e in self.history["training"].keys())
        return [self.history["training"][str(e)]["loss"] for e in epochs]

    def get_validation_rmse(self) -> list[float]:
        """Get all validation RMSE values in epoch order.

        Returns:
            List of validation RMSE values ordered by epoch.
        """
        if not self.history["validation"]:
            return []

        epochs = sorted(int(e) for e in self.history["validation"].keys())
        return [self.history["validation"][str(e)]["rmse"] for e in epochs]

    def get_validation_mae(self) -> list[Optional[float]]:
        """Get all validation MAE values in epoch order.

        Returns:
            List of validation MAE values ordered by epoch.
        """
        if not self.history["validation"]:
            return []

        epochs = sorted(int(e) for e in self.history["validation"].keys())
        return [self.history["validation"][str(e)]["mae"] for e in epochs]

    def get_final_metrics(self) -> dict[str, Optional[float]]:
        """Get the final epoch's validation metrics.

        Returns:
            Dictionary with 'rmse' and 'mae' from the last validation epoch,
            or empty dict if no validation metrics logged.
        """
        if not self.history["validation"]:
            return {}

        last_epoch = max(int(e) for e in self.history["validation"].keys())
        return self.history["validation"][str(last_epoch)]

    def reset(self) -> None:
        """Clear all logged metrics."""
        self.history = {"validation": {}, "training": {}}

    @property
    def num_epochs(self) -> int:
        """Get the number of epochs logged.

        Returns:
            Number of epochs with training or validation metrics.
        """
        train_epochs = set(int(e) for e in self.history["training"].keys())
        val_epochs = set(int(e) for e in self.history["validation"].keys())
        return len(train_epochs | val_epochs)
