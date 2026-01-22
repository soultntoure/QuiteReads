"""Unit tests for MetricsLogger class."""

import pytest

from app.application.reporting.metrics_logger import MetricsLogger


class TestMetricsLoggerInit:
    """Tests for MetricsLogger initialization."""

    def test_default_initialization(self):
        """Should initialize with empty history."""
        logger = MetricsLogger()

        assert logger.history == {"validation": {}, "training": {}}

    def test_history_structure(self):
        """Should have validation and training sub-dicts."""
        logger = MetricsLogger()

        assert "validation" in logger.history
        assert "training" in logger.history
        assert isinstance(logger.history["validation"], dict)
        assert isinstance(logger.history["training"], dict)


class TestLogTraining:
    """Tests for log_training method."""

    def test_logs_training_loss(self):
        """Should log training loss for epoch."""
        logger = MetricsLogger()

        logger.log_training(epoch=0, loss=0.5)

        assert logger.history["training"]["0"] == {"loss": 0.5}

    def test_logs_multiple_epochs(self):
        """Should log training loss for multiple epochs."""
        logger = MetricsLogger()

        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=1, loss=0.4)
        logger.log_training(epoch=2, loss=0.3)

        assert logger.history["training"]["0"]["loss"] == 0.5
        assert logger.history["training"]["1"]["loss"] == 0.4
        assert logger.history["training"]["2"]["loss"] == 0.3

    def test_overwrites_same_epoch(self):
        """Logging same epoch should overwrite previous value."""
        logger = MetricsLogger()

        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=0, loss=0.3)

        assert logger.history["training"]["0"]["loss"] == 0.3


class TestLogValidation:
    """Tests for log_validation method."""

    def test_logs_validation_rmse(self):
        """Should log validation RMSE for epoch."""
        logger = MetricsLogger()

        logger.log_validation(epoch=0, rmse=1.2)

        assert logger.history["validation"]["0"]["rmse"] == 1.2

    def test_logs_validation_rmse_and_mae(self):
        """Should log both RMSE and MAE when provided."""
        logger = MetricsLogger()

        logger.log_validation(epoch=0, rmse=1.2, mae=0.9)

        assert logger.history["validation"]["0"]["rmse"] == 1.2
        assert logger.history["validation"]["0"]["mae"] == 0.9

    def test_mae_defaults_to_none(self):
        """MAE should default to None if not provided."""
        logger = MetricsLogger()

        logger.log_validation(epoch=0, rmse=1.2)

        assert logger.history["validation"]["0"]["mae"] is None

    def test_logs_multiple_epochs(self):
        """Should log validation metrics for multiple epochs."""
        logger = MetricsLogger()

        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)
        logger.log_validation(epoch=1, rmse=1.3, mae=1.0)
        logger.log_validation(epoch=2, rmse=1.1, mae=0.8)

        assert logger.history["validation"]["0"]["rmse"] == 1.5
        assert logger.history["validation"]["1"]["rmse"] == 1.3
        assert logger.history["validation"]["2"]["rmse"] == 1.1


class TestGetTrainingLosses:
    """Tests for get_training_losses method."""

    def test_returns_empty_list_when_no_training(self):
        """Should return empty list if no training logged."""
        logger = MetricsLogger()

        losses = logger.get_training_losses()

        assert losses == []

    def test_returns_losses_in_epoch_order(self):
        """Should return losses ordered by epoch."""
        logger = MetricsLogger()
        # Log out of order
        logger.log_training(epoch=2, loss=0.3)
        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=1, loss=0.4)

        losses = logger.get_training_losses()

        assert losses == [0.5, 0.4, 0.3]


class TestGetValidationRmse:
    """Tests for get_validation_rmse method."""

    def test_returns_empty_list_when_no_validation(self):
        """Should return empty list if no validation logged."""
        logger = MetricsLogger()

        rmse_values = logger.get_validation_rmse()

        assert rmse_values == []

    def test_returns_rmse_in_epoch_order(self):
        """Should return RMSE values ordered by epoch."""
        logger = MetricsLogger()
        # Log out of order
        logger.log_validation(epoch=2, rmse=1.1)
        logger.log_validation(epoch=0, rmse=1.5)
        logger.log_validation(epoch=1, rmse=1.3)

        rmse_values = logger.get_validation_rmse()

        assert rmse_values == [1.5, 1.3, 1.1]


class TestGetValidationMae:
    """Tests for get_validation_mae method."""

    def test_returns_empty_list_when_no_validation(self):
        """Should return empty list if no validation logged."""
        logger = MetricsLogger()

        mae_values = logger.get_validation_mae()

        assert mae_values == []

    def test_returns_mae_in_epoch_order(self):
        """Should return MAE values ordered by epoch."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)
        logger.log_validation(epoch=1, rmse=1.3, mae=1.0)
        logger.log_validation(epoch=2, rmse=1.1, mae=0.8)

        mae_values = logger.get_validation_mae()

        assert mae_values == [1.2, 1.0, 0.8]

    def test_handles_none_mae_values(self):
        """Should handle None MAE values."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5)
        logger.log_validation(epoch=1, rmse=1.3, mae=1.0)

        mae_values = logger.get_validation_mae()

        assert mae_values == [None, 1.0]


class TestGetFinalMetrics:
    """Tests for get_final_metrics method."""

    def test_returns_empty_dict_when_no_validation(self):
        """Should return empty dict if no validation logged."""
        logger = MetricsLogger()

        final = logger.get_final_metrics()

        assert final == {}

    def test_returns_last_epoch_metrics(self):
        """Should return metrics from the last validation epoch."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)
        logger.log_validation(epoch=1, rmse=1.3, mae=1.0)
        logger.log_validation(epoch=2, rmse=1.1, mae=0.8)

        final = logger.get_final_metrics()

        assert final == {"rmse": 1.1, "mae": 0.8}

    def test_handles_non_sequential_epochs(self):
        """Should find max epoch even if not sequential."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)
        logger.log_validation(epoch=5, rmse=1.0, mae=0.7)
        logger.log_validation(epoch=2, rmse=1.2, mae=0.9)

        final = logger.get_final_metrics()

        # Epoch 5 is the highest
        assert final == {"rmse": 1.0, "mae": 0.7}


class TestReset:
    """Tests for reset method."""

    def test_clears_all_metrics(self):
        """Should clear all logged metrics."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)

        logger.reset()

        assert logger.history == {"validation": {}, "training": {}}

    def test_can_log_after_reset(self):
        """Should be able to log new metrics after reset."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.reset()
        logger.log_training(epoch=0, loss=0.3)

        assert logger.history["training"]["0"]["loss"] == 0.3


class TestNumEpochs:
    """Tests for num_epochs property."""

    def test_returns_zero_for_empty_logger(self):
        """Should return 0 when no metrics logged."""
        logger = MetricsLogger()

        assert logger.num_epochs == 0

    def test_counts_training_epochs(self):
        """Should count training epochs."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=1, loss=0.4)

        assert logger.num_epochs == 2

    def test_counts_validation_epochs(self):
        """Should count validation epochs."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5)
        logger.log_validation(epoch=1, rmse=1.3)
        logger.log_validation(epoch=2, rmse=1.1)

        assert logger.num_epochs == 3

    def test_counts_unique_epochs_across_both(self):
        """Should count unique epochs from both training and validation."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=1, loss=0.4)
        logger.log_validation(epoch=0, rmse=1.5)
        logger.log_validation(epoch=1, rmse=1.3)

        # Epochs 0 and 1 appear in both, should count as 2
        assert logger.num_epochs == 2

    def test_handles_non_overlapping_epochs(self):
        """Should handle non-overlapping training and validation epochs."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.log_training(epoch=1, loss=0.4)
        logger.log_validation(epoch=2, rmse=1.5)
        logger.log_validation(epoch=3, rmse=1.3)

        # Epochs 0, 1 from training + 2, 3 from validation = 4 unique
        assert logger.num_epochs == 4


class TestHistoryFormat:
    """Tests for history format compatibility with federated training."""

    def test_history_uses_string_epoch_keys(self):
        """Epoch keys should be strings (for JSON serialization)."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)
        logger.log_validation(epoch=0, rmse=1.5)

        assert "0" in logger.history["training"]
        assert "0" in logger.history["validation"]
        assert 0 not in logger.history["training"]
        assert 0 not in logger.history["validation"]

    def test_training_entry_structure(self):
        """Training entries should have expected structure."""
        logger = MetricsLogger()
        logger.log_training(epoch=0, loss=0.5)

        entry = logger.history["training"]["0"]
        assert entry == {"loss": 0.5}

    def test_validation_entry_structure(self):
        """Validation entries should have expected structure."""
        logger = MetricsLogger()
        logger.log_validation(epoch=0, rmse=1.5, mae=1.2)

        entry = logger.history["validation"]["0"]
        assert entry == {"rmse": 1.5, "mae": 1.2}
