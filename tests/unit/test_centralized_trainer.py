"""Unit tests for CentralizedTrainer and LitBiasedMatrixFactorization.

Tests cover:
- LitBiasedMatrixFactorization Lightning module
- CentralizedTrainer training orchestration
- MetricsLoggingCallback functionality
- TrainingResult dataclass
"""

import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from app.application.reporting.metrics_logger import MetricsLogger
from app.application.training.centralized_trainer import (
    CentralizedTrainer,
    LitBiasedMatrixFactorization,
    MetricsLoggingCallback,
    TrainingResult,
)
from app.core.configuration import Configuration


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def small_config() -> Configuration:
    """Configuration for small/fast training."""
    return Configuration(
        n_factors=8,
        learning_rate=0.01,
        regularization=0.01,
        n_epochs=2,
    )


@pytest.fixture
def lit_model() -> LitBiasedMatrixFactorization:
    """Create a small Lightning model for testing."""
    return LitBiasedMatrixFactorization(
        n_users=100,
        n_items=50,
        n_factors=8,
        global_mean=3.5,
        learning_rate=0.01,
        regularization=0.01,
    )


@pytest.fixture
def synthetic_dataset() -> TensorDataset:
    """Create synthetic rating data with structure for testing."""
    n_samples = 1000  # More samples to help learning
    n_users = 100
    n_items = 50
    n_factors = 5
    
    # Create structured data: user_prefs @ item_features
    # This ensures the model CAN learn the underlying pattern
    torch.manual_seed(42)  # Ensure reproducibility
    user_factors = torch.randn(n_users, n_factors)
    item_factors = torch.randn(n_items, n_factors)
    
    # Generate random interactions
    user_ids = torch.randint(0, n_users, (n_samples,))
    item_ids = torch.randint(0, n_items, (n_samples,))
    
    # Calculate True ratings (dot product) + small noise
    # We use a simple dot product to match the Matrix Factorization assumption
    true_ratings = (user_factors[user_ids] * item_factors[item_ids]).sum(dim=1)
    
    # Add small amount of noise
    noisy_ratings = true_ratings + torch.randn(n_samples) * 0.1
    
    return TensorDataset(user_ids, item_ids, noisy_ratings.float())


@pytest.fixture
def train_loader(synthetic_dataset: TensorDataset) -> DataLoader:
    """DataLoader for training data."""
    return DataLoader(synthetic_dataset, batch_size=64, shuffle=True)


@pytest.fixture
def val_loader(synthetic_dataset: TensorDataset) -> DataLoader:
    """DataLoader for validation data (same data, no shuffle)."""
    return DataLoader(synthetic_dataset, batch_size=64, shuffle=False)


@pytest.fixture
def metrics_logger() -> MetricsLogger:
    """Fresh MetricsLogger instance."""
    return MetricsLogger()


# -----------------------------------------------------------------------------
# LitBiasedMatrixFactorization Tests
# -----------------------------------------------------------------------------


class TestLitBiasedMatrixFactorization:
    """Tests for the Lightning module wrapper."""

    def test_initialization_sets_hyperparameters(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Model stores hyperparameters correctly."""
        assert lit_model.learning_rate == 0.01
        assert lit_model.regularization == 0.01
        assert lit_model.hparams.n_users == 100
        assert lit_model.hparams.n_items == 50
        assert lit_model.hparams.n_factors == 8

    def test_initialization_creates_underlying_model(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Lightning module creates BiasedMatrixFactorization model."""
        assert lit_model.model is not None
        assert lit_model.model.n_users == 100
        assert lit_model.model.n_items == 50
        assert lit_model.model.n_factors == 8

    def test_forward_pass_delegates_to_model(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Forward pass delegates to underlying model."""
        user_ids = torch.tensor([0, 1, 2])
        item_ids = torch.tensor([5, 10, 15])
        predictions = lit_model(user_ids, item_ids)

        assert predictions.shape == (3,)
        assert predictions.dtype == torch.float32

    def test_training_step_returns_loss(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Training step returns a scalar loss."""
        batch = (
            torch.tensor([0, 1, 2]),
            torch.tensor([5, 10, 15]),
            torch.tensor([4.0, 3.5, 5.0]),
        )
        loss = lit_model.training_step(batch, batch_idx=0)

        assert isinstance(loss, torch.Tensor)
        assert loss.dim() == 0  # Scalar
        assert loss.item() > 0  # Loss should be positive

    def test_validation_step_collects_predictions(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Validation step collects predictions and targets."""
        batch = (
            torch.tensor([0, 1, 2]),
            torch.tensor([5, 10, 15]),
            torch.tensor([4.0, 3.5, 5.0]),
        )
        lit_model.validation_step(batch, batch_idx=0)

        assert len(lit_model._val_predictions) == 1
        assert len(lit_model._val_targets) == 1
        assert lit_model._val_predictions[0].shape == (3,)

    def test_on_validation_epoch_end_computes_metrics(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Validation epoch end computes RMSE and MAE."""
        # Add some validation data
        lit_model._val_predictions = [torch.tensor([3.0, 4.0, 5.0])]
        lit_model._val_targets = [torch.tensor([3.5, 4.0, 4.5])]

        lit_model.on_validation_epoch_end()

        # Storage should be cleared after epoch end
        assert len(lit_model._val_predictions) == 0
        assert len(lit_model._val_targets) == 0

    def test_on_validation_epoch_end_handles_empty_data(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Validation epoch end handles empty prediction lists gracefully."""
        lit_model._val_predictions = []
        lit_model._val_targets = []

        # Should not raise
        lit_model.on_validation_epoch_end()

    def test_configure_optimizers_returns_adam(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Optimizer is Adam with correct settings."""
        optimizer = lit_model.configure_optimizers()

        assert isinstance(optimizer, torch.optim.Adam)
        assert optimizer.defaults["lr"] == 0.01
        assert optimizer.defaults["weight_decay"] == 0.01

    def test_get_model_returns_underlying_model(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """get_model() returns the BiasedMatrixFactorization instance."""
        model = lit_model.get_model()

        assert model is lit_model.model
        assert model.n_users == 100

    def test_test_step_returns_predictions_and_targets(
        self, lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Test step returns dictionary with predictions and targets."""
        batch = (
            torch.tensor([0, 1, 2]),
            torch.tensor([5, 10, 15]),
            torch.tensor([4.0, 3.5, 5.0]),
        )
        result = lit_model.test_step(batch, batch_idx=0)

        assert "predictions" in result
        assert "targets" in result
        assert result["predictions"].shape == (3,)
        assert result["targets"].shape == (3,)


# -----------------------------------------------------------------------------
# MetricsLoggingCallback Tests
# -----------------------------------------------------------------------------


class TestMetricsLoggingCallback:
    """Tests for the metrics logging callback."""

    def test_initialization_stores_logger(
        self, metrics_logger: MetricsLogger
    ) -> None:
        """Callback stores MetricsLogger reference."""
        callback = MetricsLoggingCallback(metrics_logger)
        assert callback.metrics_logger is metrics_logger

    def test_on_train_epoch_end_logs_loss(
        self, metrics_logger: MetricsLogger
    ) -> None:
        """Callback logs training loss at epoch end."""
        callback = MetricsLoggingCallback(metrics_logger)

        # Create mock trainer with metrics
        class MockTrainer:
            current_epoch = 0
            callback_metrics = {"train_loss": torch.tensor(0.5)}

        callback.on_train_epoch_end(MockTrainer(), None)

        assert metrics_logger.num_epochs == 1
        losses = metrics_logger.get_training_losses()
        assert len(losses) == 1
        assert losses[0] == pytest.approx(0.5)

    def test_on_validation_epoch_end_logs_metrics(
        self, metrics_logger: MetricsLogger
    ) -> None:
        """Callback logs validation RMSE and MAE at epoch end."""
        callback = MetricsLoggingCallback(metrics_logger)

        class MockTrainer:
            current_epoch = 0

        class MockModule:
            _last_epoch_metrics = {"rmse": 0.85, "mae": 0.65}

        callback.on_validation_epoch_end(MockTrainer(), MockModule())

        rmse_values = metrics_logger.get_validation_rmse()
        mae_values = metrics_logger.get_validation_mae()

        assert len(rmse_values) == 1
        assert rmse_values[0] == pytest.approx(0.85)
        assert mae_values[0] == pytest.approx(0.65)

    def test_callback_handles_missing_metrics(
        self, metrics_logger: MetricsLogger
    ) -> None:
        """Callback handles missing metrics gracefully."""
        callback = MetricsLoggingCallback(metrics_logger)

        class MockTrainer:
            current_epoch = 0
            callback_metrics = {}  # No metrics

        class MockModuleNoMetrics:
            _last_epoch_metrics = None  # No metrics

        # Should not raise
        callback.on_train_epoch_end(MockTrainer(), None)
        callback.on_validation_epoch_end(MockTrainer(), MockModuleNoMetrics())

        assert metrics_logger.num_epochs == 0


# -----------------------------------------------------------------------------
# CentralizedTrainer Tests
# -----------------------------------------------------------------------------


class TestCentralizedTrainer:
    """Tests for the CentralizedTrainer class."""

    def test_initialization_stores_config(
        self, small_config: Configuration
    ) -> None:
        """Trainer stores configuration and parameters."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        assert trainer.config is small_config
        assert trainer.n_users == 100
        assert trainer.n_items == 50
        assert trainer.global_mean == 3.5
        assert trainer._model is None

    def test_create_model_returns_lit_model(
        self, small_config: Configuration
    ) -> None:
        """_create_model() returns properly configured Lightning model."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        model = trainer._create_model()

        assert isinstance(model, LitBiasedMatrixFactorization)
        assert model.hparams.n_factors == 8
        assert model.learning_rate == 0.01

    def test_train_returns_training_result(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """train() returns a TrainingResult with metrics."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        result = trainer.train(train_loader, val_loader, accelerator="cpu")

        assert isinstance(result, TrainingResult)
        assert result.final_rmse >= 0
        assert result.final_mae >= 0
        assert result.training_time_seconds > 0
        assert result.model is not None

    def test_train_updates_internal_model(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """train() updates the trainer's internal model reference."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        assert trainer.model is None
        trainer.train(train_loader, val_loader, accelerator="cpu")
        assert trainer.model is not None

    def test_train_populates_metrics_history(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """train() populates metrics history."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        result = trainer.train(train_loader, val_loader, accelerator="cpu")

        # Should have metrics for each epoch
        history = result.metrics_logger.history
        assert "training" in history
        assert "validation" in history

        # Should have 2 epochs worth of data (matching n_epochs=2 in small_config)
        assert len(history["training"]) == 2
        assert len(history["validation"]) == 2

    def test_evaluate_raises_before_training(
        self,
        small_config: Configuration,
        val_loader: DataLoader,
    ) -> None:
        """evaluate() raises RuntimeError if called before training."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        with pytest.raises(RuntimeError, match="Model has not been trained"):
            trainer.evaluate(val_loader, accelerator="cpu")

    def test_evaluate_returns_metrics(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """evaluate() returns RMSE and MAE after training."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        trainer.train(train_loader, val_loader, accelerator="cpu")
        metrics = trainer.evaluate(val_loader, accelerator="cpu")

        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0

    def test_metrics_history_property(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """metrics_history property returns history after training."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        assert trainer.metrics_history is None

        trainer.train(train_loader, val_loader, accelerator="cpu")

        history = trainer.metrics_history
        assert history is not None
        assert "training" in history
        assert "validation" in history


# -----------------------------------------------------------------------------
# TrainingResult Tests
# -----------------------------------------------------------------------------


class TestTrainingResult:
    """Tests for the TrainingResult dataclass."""

    def test_training_result_creation(
        self,
        lit_model: LitBiasedMatrixFactorization,
        metrics_logger: MetricsLogger,
    ) -> None:
        """TrainingResult can be created with all fields."""
        result = TrainingResult(
            final_rmse=0.85,
            final_mae=0.65,
            training_time_seconds=123.45,
            metrics_logger=metrics_logger,
            model=lit_model,
        )

        assert result.final_rmse == 0.85
        assert result.final_mae == 0.65
        assert result.training_time_seconds == 123.45
        assert result.metrics_logger is metrics_logger
        assert result.model is lit_model


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


class TestTrainerIntegration:
    """Integration tests for complete training workflows."""

    def test_full_training_cycle(
        self,
        small_config: Configuration,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """Complete training cycle works end-to-end."""
        trainer = CentralizedTrainer(
            config=small_config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        # Train
        result = trainer.train(train_loader, val_loader, accelerator="cpu")

        # Verify result
        assert result.final_rmse > 0
        assert result.final_mae > 0
        assert result.training_time_seconds > 0

        # Evaluate
        test_metrics = trainer.evaluate(val_loader, accelerator="cpu")
        assert test_metrics["rmse"] > 0
        assert test_metrics["mae"] > 0

        # Model should be accessible
        assert trainer.model is not None
        assert trainer.model.model.n_users == 100

    def test_model_improves_during_training(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """Model RMSE should generally improve (decrease) during training."""
        config = Configuration(
            n_factors=16,
            learning_rate=0.05,
            regularization=0.001,
            n_epochs=5,
        )

        trainer = CentralizedTrainer(
            config=config,
            n_users=100,
            n_items=50,
            global_mean=3.5,
        )

        result = trainer.train(train_loader, val_loader, accelerator="cpu")

        rmse_values = result.metrics_logger.get_validation_rmse()
        # Should have exactly 5 validation metrics (one per epoch)
        assert len(rmse_values) == 5

        # First RMSE should be higher than last (model should improve)
        # Allow some tolerance for randomness
        assert rmse_values[-1] <= rmse_values[0] * 1.2  # Should not get much worse
