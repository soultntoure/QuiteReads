"""Centralized training module for BiasedMatrixFactorization.

Uses PyTorch Lightning to wrap the BiasedMatrixFactorization model,
providing clean training/validation/test loops with built-in logging.

This serves as the baseline trainer for comparing against federated approaches.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pytorch_lightning as pl
import torch
import torch.nn as nn
from pytorch_lightning.callbacks import Callback
from torch.utils.data import DataLoader

from app.application.reporting.metrics_calculator import compute_metrics
from app.application.reporting.metrics_logger import MetricsLogger
from app.core.configuration import Configuration
from app.core.models.matrix_factorization import BiasedMatrixFactorization


class LitBiasedMatrixFactorization(pl.LightningModule):
    """PyTorch Lightning wrapper for BiasedMatrixFactorization.

    Encapsulates training, validation, and test logic with proper logging
    and metric tracking. Designed for clean integration with Flower FL.

    Attributes:
        model: The underlying BiasedMatrixFactorization model.
        learning_rate: Optimizer learning rate.
        regularization: L2 regularization weight (weight_decay).

    Example:
        >>> lit_model = LitBiasedMatrixFactorization(
        ...     n_users=5949,
        ...     n_items=2856,
        ...     n_factors=50,
        ...     global_mean=4.07,
        ...     learning_rate=0.01,
        ... )
        >>> trainer = pl.Trainer(max_epochs=20)
        >>> trainer.fit(lit_model, train_loader, val_loader)
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        n_factors: int = 20,
        global_mean: float = 0.0,
        learning_rate: float = 0.02,
        regularization: float = 0.003,
    ):
        """Initialize the Lightning module.

        Args:
            n_users: Number of unique users.
            n_items: Number of unique items.
            n_factors: Dimension of latent factors.
            global_mean: Initial global mean rating.
            learning_rate: Optimizer learning rate.
            regularization: L2 regularization weight.
        """
        super().__init__()
        self.save_hyperparameters()

        self.model = BiasedMatrixFactorization(
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
        )

        self.learning_rate = learning_rate
        self.regularization = regularization
        self.loss_fn = nn.MSELoss()

        # Storage for epoch-level metrics (collected during validation)
        self._val_predictions: list[torch.Tensor] = []
        self._val_targets: list[torch.Tensor] = []
        # Store last computed metrics for callback to read
        self._last_epoch_metrics: Optional[dict[str, float]] = None

    def forward(self, user_ids: torch.Tensor, item_ids: torch.Tensor) -> torch.Tensor:
        """Forward pass delegates to underlying model."""
        return self.model(user_ids, item_ids)

    def training_step(self, batch: tuple, batch_idx: int) -> torch.Tensor:
        """Perform a single training step.

        Args:
            batch: Tuple of (user_ids, item_ids, ratings).
            batch_idx: Index of the current batch.

        Returns:
            Training loss for this batch.
        """
        user_ids, item_ids, ratings = batch
        predictions = self(user_ids, item_ids)
        loss = self.loss_fn(predictions, ratings)

        self.log("train_loss", loss, on_step=False, on_epoch=True, prog_bar=True)
        return loss

    def validation_step(self, batch: tuple, batch_idx: int) -> None:
        """Perform a single validation step.

        Collects predictions and targets for epoch-level metric computation.

        Args:
            batch: Tuple of (user_ids, item_ids, ratings).
            batch_idx: Index of the current batch.
        """
        user_ids, item_ids, ratings = batch
        predictions = self(user_ids, item_ids)

        self._val_predictions.append(predictions.detach())
        self._val_targets.append(ratings.detach())

    def on_validation_epoch_end(self) -> None:
        """Compute and log validation metrics at epoch end."""
        if not self._val_predictions:
            return

        all_predictions = torch.cat(self._val_predictions)
        all_targets = torch.cat(self._val_targets)

        metrics = compute_metrics(all_predictions, all_targets)

        # Store for callback to read (guaranteed timing)
        self._last_epoch_metrics = {
            "rmse": metrics["rmse"],
            "mae": metrics["mae"],
        }

        self.log("val_rmse", metrics["rmse"], prog_bar=True)
        self.log("val_mae", metrics["mae"], prog_bar=True)

        # Clear storage for next epoch
        self._val_predictions.clear()
        self._val_targets.clear()

    def test_step(self, batch: tuple, batch_idx: int) -> dict[str, torch.Tensor]:
        """Perform a single test step.

        Args:
            batch: Tuple of (user_ids, item_ids, ratings).
            batch_idx: Index of the current batch.

        Returns:
            Dictionary with predictions and targets for metric computation.
        """
        user_ids, item_ids, ratings = batch
        predictions = self(user_ids, item_ids)

        return {"predictions": predictions, "targets": ratings}

    def configure_optimizers(self) -> torch.optim.Optimizer:
        """Configure the optimizer with L2 regularization."""
        return torch.optim.Adam(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=self.regularization,
        )

    def get_model(self) -> BiasedMatrixFactorization:
        """Return the underlying model (useful for federated learning)."""
        return self.model


class MetricsLoggingCallback(Callback):
    """Lightning callback that logs metrics to MetricsLogger.

    Bridges Lightning's logging system with the application's MetricsLogger
    for persistence to the database.
    """

    def __init__(self, metrics_logger: MetricsLogger):
        """Initialize with a MetricsLogger instance.

        Args:
            metrics_logger: The MetricsLogger to write metrics to.
        """
        super().__init__()
        self.metrics_logger = metrics_logger

    def on_train_epoch_end(
        self,
        trainer: pl.Trainer,
        pl_module: pl.LightningModule,
    ) -> None:
        """Log training loss at epoch end."""
        metrics = trainer.callback_metrics
        epoch = trainer.current_epoch

        if "train_loss" in metrics:
            loss = float(metrics["train_loss"])
            self.metrics_logger.log_training(epoch, loss)

    def on_validation_epoch_end(
        self,
        trainer: pl.Trainer,
        pl_module: pl.LightningModule,
    ) -> None:
        """Log validation metrics at epoch end.

        Reads directly from pl_module._last_epoch_metrics which is set
        by LitBiasedMatrixFactorization.on_validation_epoch_end before
        this callback runs, guaranteeing metrics availability.
        """
        epoch = trainer.current_epoch

        # Read from module's stored metrics (guaranteed to exist after module hook)
        if hasattr(pl_module, "_last_epoch_metrics") and pl_module._last_epoch_metrics:
            rmse = float(pl_module._last_epoch_metrics["rmse"])
            mae = float(pl_module._last_epoch_metrics["mae"])
            self.metrics_logger.log_validation(epoch, rmse, mae)


@dataclass
class TrainingResult:
    """Result of a centralized training run.

    Attributes:
        final_rmse: Final validation RMSE.
        final_mae: Final validation MAE.
        training_time_seconds: Total training time.
        metrics_logger: Logger with per-epoch metrics history.
        model: Trained Lightning model.
    """

    final_rmse: float
    final_mae: float
    training_time_seconds: float
    metrics_logger: MetricsLogger
    model: LitBiasedMatrixFactorization


class CentralizedTrainer:
    """Trainer for centralized matrix factorization experiments.

    Orchestrates the training loop using PyTorch Lightning, managing
    model initialization, training execution, and metrics collection.

    Example:
        >>> trainer = CentralizedTrainer(
        ...     config=Configuration(n_factors=50, n_epochs=20, learning_rate=0.01),
        ...     n_users=5949,
        ...     n_items=2856,
        ...     global_mean=4.07,
        ... )
        >>> result = trainer.train(train_loader, val_loader)
        >>> print(f"Final RMSE: {result.final_rmse}")
    """

    def __init__(
        self,
        config: Configuration,
        n_users: int,
        n_items: int,
        global_mean: float,
        checkpoint_dir: Optional[Path] = None,
    ):
        """Initialize the trainer.

        Args:
            config: Experiment configuration with hyperparameters.
            n_users: Number of unique users in the dataset.
            n_items: Number of unique items in the dataset.
            global_mean: Global mean rating from training data.
            checkpoint_dir: Optional directory for saving checkpoints.
        """
        self.config = config
        self.n_users = n_users
        self.n_items = n_items
        self.global_mean = global_mean
        self.checkpoint_dir = checkpoint_dir

        self._model: Optional[LitBiasedMatrixFactorization] = None
        self._metrics_logger: Optional[MetricsLogger] = None

    def _create_model(self) -> LitBiasedMatrixFactorization:
        """Create and return a new Lightning model instance."""
        return LitBiasedMatrixFactorization(
            n_users=self.n_users,
            n_items=self.n_items,
            n_factors=self.config.n_factors,
            global_mean=self.global_mean,
            learning_rate=self.config.learning_rate,
            regularization=self.config.regularization,
        )

    def _create_trainer(
        self,
        metrics_logger: MetricsLogger,
        accelerator: str = "auto",
    ) -> pl.Trainer:
        """Create and configure a PyTorch Lightning Trainer.

        Args:
            metrics_logger: Logger for capturing metrics via callback.
            accelerator: Device accelerator ("auto", "cpu", "gpu").

        Returns:
            Configured Lightning Trainer.
        """
        callbacks = [MetricsLoggingCallback(metrics_logger)]

        trainer_kwargs: dict[str, Any] = {
            "max_epochs": self.config.n_epochs,
            "accelerator": accelerator,
            "callbacks": callbacks,
            "enable_progress_bar": True,
            "enable_model_summary": False,
            "logger": False,  # Disable Lightning's built-in logger
        }

        if self.checkpoint_dir:
            trainer_kwargs["default_root_dir"] = str(self.checkpoint_dir)

        return pl.Trainer(**trainer_kwargs)

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        accelerator: str = "auto",
    ) -> TrainingResult:
        """Run centralized training.

        Args:
            train_loader: DataLoader for training data.
            val_loader: DataLoader for validation data.
            accelerator: Device accelerator ("auto", "cpu", "gpu").

        Returns:
            TrainingResult with final metrics and trained model.
        """
        self._metrics_logger = MetricsLogger()
        self._model = self._create_model()

        trainer = self._create_trainer(self._metrics_logger, accelerator)

        start_time = time.time()
        trainer.fit(self._model, train_loader, val_loader)
        training_time = time.time() - start_time

        # Extract final metrics
        final_metrics = self._metrics_logger.get_final_metrics()
        final_rmse = final_metrics.get("rmse", 0.0) or 0.0
        final_mae = final_metrics.get("mae", 0.0) or 0.0

        return TrainingResult(
            final_rmse=final_rmse,
            final_mae=final_mae,
            training_time_seconds=training_time,
            metrics_logger=self._metrics_logger,
            model=self._model,
        )

    def evaluate(
        self,
        test_loader: DataLoader,
        accelerator: str = "auto",
    ) -> dict[str, float]:
        """Evaluate the trained model on test data.

        Args:
            test_loader: DataLoader for test data.
            accelerator: Device accelerator.

        Returns:
            Dictionary with test metrics (rmse, mae).

        Raises:
            RuntimeError: If called before training.
        """
        if self._model is None:
            raise RuntimeError("Model has not been trained. Call train() first.")

        self._model.eval()
        all_predictions = []
        all_targets = []

        device = next(self._model.parameters()).device

        with torch.no_grad():
            for batch in test_loader:
                user_ids, item_ids, ratings = batch
                user_ids = user_ids.to(device)
                item_ids = item_ids.to(device)

                predictions = self._model(user_ids, item_ids)
                all_predictions.append(predictions.cpu())
                all_targets.append(ratings)

        predictions_tensor = torch.cat(all_predictions)
        targets_tensor = torch.cat(all_targets)

        return compute_metrics(predictions_tensor, targets_tensor)

    @property
    def model(self) -> Optional[LitBiasedMatrixFactorization]:
        """Return the trained model, if available."""
        return self._model

    @property
    def metrics_history(self) -> Optional[dict]:
        """Return the metrics history, if available."""
        return self._metrics_logger.history if self._metrics_logger else None
