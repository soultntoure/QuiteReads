"""Unit tests for metrics calculator functions."""

import math

import pytest
import torch

from app.application.reporting.metrics_calculator import (
    compute_mae,
    compute_metrics,
    compute_rmse,
)


class TestComputeRmse:
    """Tests for compute_rmse function."""

    def test_perfect_predictions(self):
        """RMSE should be 0 for perfect predictions."""
        predictions = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        actuals = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

        rmse = compute_rmse(predictions, actuals)

        assert rmse == 0.0

    def test_known_rmse_value(self):
        """RMSE should match hand-calculated value."""
        # Errors: [1, -1, 2, -2] -> squared: [1, 1, 4, 4] -> mean: 2.5 -> sqrt: ~1.58
        predictions = torch.tensor([2.0, 2.0, 5.0, 1.0])
        actuals = torch.tensor([1.0, 3.0, 3.0, 3.0])

        rmse = compute_rmse(predictions, actuals)

        expected = math.sqrt(2.5)
        assert abs(rmse - expected) < 1e-6

    def test_accepts_python_lists(self):
        """Should accept Python lists as input."""
        predictions = [1.0, 2.0, 3.0]
        actuals = [1.5, 2.5, 3.5]

        rmse = compute_rmse(predictions, actuals)

        # Errors: [-0.5, -0.5, -0.5] -> squared: [0.25, 0.25, 0.25] -> mean: 0.25 -> sqrt: 0.5
        assert abs(rmse - 0.5) < 1e-6

    def test_single_value(self):
        """Should work with single value."""
        rmse = compute_rmse([3.0], [1.0])

        assert rmse == 2.0

    def test_empty_input_raises_error(self):
        """Should raise ValueError for empty inputs."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_rmse([], [])

    def test_mismatched_shapes_raises_error(self):
        """Should raise ValueError for mismatched shapes."""
        predictions = torch.tensor([1.0, 2.0, 3.0])
        actuals = torch.tensor([1.0, 2.0])

        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_rmse(predictions, actuals)


class TestComputeMae:
    """Tests for compute_mae function."""

    def test_perfect_predictions(self):
        """MAE should be 0 for perfect predictions."""
        predictions = torch.tensor([1.0, 2.0, 3.0])
        actuals = torch.tensor([1.0, 2.0, 3.0])

        mae = compute_mae(predictions, actuals)

        assert mae == 0.0

    def test_known_mae_value(self):
        """MAE should match hand-calculated value."""
        # Errors: [1, -1, 2, -2] -> abs: [1, 1, 2, 2] -> mean: 1.5
        predictions = torch.tensor([2.0, 2.0, 5.0, 1.0])
        actuals = torch.tensor([1.0, 3.0, 3.0, 3.0])

        mae = compute_mae(predictions, actuals)

        assert abs(mae - 1.5) < 1e-6

    def test_accepts_python_lists(self):
        """Should accept Python lists as input."""
        predictions = [1.0, 2.0, 3.0]
        actuals = [2.0, 3.0, 4.0]

        mae = compute_mae(predictions, actuals)

        assert mae == 1.0

    def test_single_value(self):
        """Should work with single value."""
        mae = compute_mae([5.0], [2.0])

        assert mae == 3.0

    def test_empty_input_raises_error(self):
        """Should raise ValueError for empty inputs."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_mae(torch.tensor([]), torch.tensor([]))

    def test_mismatched_shapes_raises_error(self):
        """Should raise ValueError for mismatched shapes."""
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_mae([1.0, 2.0], [1.0])


class TestComputeMetrics:
    """Tests for compute_metrics function."""

    def test_returns_both_metrics(self):
        """Should return dictionary with both rmse and mae."""
        predictions = torch.tensor([1.0, 2.0, 3.0])
        actuals = torch.tensor([1.0, 2.0, 3.0])

        metrics = compute_metrics(predictions, actuals)

        assert "rmse" in metrics
        assert "mae" in metrics

    def test_values_match_individual_functions(self):
        """Values should match individual compute functions."""
        predictions = torch.tensor([2.0, 2.0, 5.0, 1.0])
        actuals = torch.tensor([1.0, 3.0, 3.0, 3.0])

        metrics = compute_metrics(predictions, actuals)
        individual_rmse = compute_rmse(predictions, actuals)
        individual_mae = compute_mae(predictions, actuals)

        assert abs(metrics["rmse"] - individual_rmse) < 1e-6
        assert abs(metrics["mae"] - individual_mae) < 1e-6

    def test_empty_input_raises_error(self):
        """Should raise ValueError for empty inputs."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_metrics([], [])

    def test_accepts_python_lists(self):
        """Should accept Python lists as input."""
        metrics = compute_metrics([1.0, 2.0], [1.5, 2.5])

        assert isinstance(metrics["rmse"], float)
        assert isinstance(metrics["mae"], float)


class TestEdgeCases:
    """Tests for edge cases and numerical properties."""

    def test_large_values(self):
        """Should handle large values correctly."""
        predictions = torch.tensor([1000.0, 2000.0, 3000.0])
        actuals = torch.tensor([1010.0, 2010.0, 3010.0])

        rmse = compute_rmse(predictions, actuals)
        mae = compute_mae(predictions, actuals)

        assert rmse == 10.0
        assert mae == 10.0

    def test_negative_values(self):
        """Should handle negative values correctly."""
        predictions = torch.tensor([-1.0, -2.0, -3.0])
        actuals = torch.tensor([-2.0, -3.0, -4.0])

        mae = compute_mae(predictions, actuals)

        assert mae == 1.0

    def test_mixed_positive_negative_errors(self):
        """Errors in opposite directions should not cancel in RMSE/MAE."""
        predictions = torch.tensor([1.0, 3.0])
        actuals = torch.tensor([2.0, 2.0])

        # Errors: [-1, 1] -> MAE: 1.0, RMSE: 1.0
        rmse = compute_rmse(predictions, actuals)
        mae = compute_mae(predictions, actuals)

        assert rmse == 1.0
        assert mae == 1.0

    def test_fractional_values(self):
        """Should handle fractional values correctly."""
        predictions = torch.tensor([0.1, 0.2, 0.3])
        actuals = torch.tensor([0.15, 0.25, 0.35])

        mae = compute_mae(predictions, actuals)

        assert abs(mae - 0.05) < 1e-6
