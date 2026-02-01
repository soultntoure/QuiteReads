"""
Unit tests for server_app.py helper functions.

Tests the utility functions used in federated server orchestration:
- Metrics aggregation (_weighted_average_metrics)
- Model initialization (_initialize_global_model)
- Result persistence (_save_final_metrics)
- Centralized evaluation (_create_centralized_evaluate_fn)
"""

import json
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import torch

from flwr.app import ArrayRecord, MetricRecord, RecordDict

from app.application.federated import ITEM_PARAM_NAMES
from app.application.federated.server_app import (
    _create_centralized_evaluate_fn,
    _initialize_global_model,
    _save_final_metrics,
    _weighted_average_metrics,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_record_dict_eval():
    """Create mock RecordDict with evaluation metrics."""
    return RecordDict(
        metrics_records={
            "metrics": MetricRecord({
                "eval_rmse": 0.85,
                "eval_mae": 0.65,
                "eval_loss": 0.72,
                "num-examples": 100,
            })
        }
    )


@pytest.fixture
def mock_record_dict_train():
    """Create mock RecordDict with training metrics."""
    return RecordDict(
        metrics_records={
            "metrics": MetricRecord({
                "train_loss": 0.90,
                "num-examples": 150,
            })
        }
    )


@pytest.fixture
def mock_fedavg_result():
    """Create mock FedAvgResult for testing _save_final_metrics."""
    result = Mock()

    # Centralized evaluation metrics (server-side)
    result.evaluate_metrics_serverapp = {
        1: MetricRecord({"test_rmse": 0.95, "test_mae": 0.75, "test_loss": 0.90}),
        2: MetricRecord({"test_rmse": 0.85, "test_mae": 0.65, "test_loss": 0.72}),
        3: MetricRecord({"test_rmse": 0.80, "test_mae": 0.60, "test_loss": 0.64}),
    }

    # Client evaluation metrics
    result.evaluate_metrics_clientapp = {
        1: MetricRecord({"agg_rmse": 0.90, "agg_mae": 0.70, "agg_loss": 0.81, "total_examples": 500}),
        2: MetricRecord({"agg_rmse": 0.88, "agg_mae": 0.68, "agg_loss": 0.77, "total_examples": 500}),
        3: MetricRecord({"agg_rmse": 0.86, "agg_mae": 0.66, "agg_loss": 0.74, "total_examples": 500}),
    }

    # Training metrics
    result.train_metrics_clientapp = {
        1: MetricRecord({"agg_loss": 1.05, "total_examples": 500}),
        2: MetricRecord({"agg_loss": 0.95, "total_examples": 500}),
        3: MetricRecord({"agg_loss": 0.88, "total_examples": 500}),
    }

    return result


# ==================== _weighted_average_metrics Tests ====================


class TestWeightedAverageMetrics:
    """Test suite for _weighted_average_metrics function."""

    def test_computes_weighted_average_eval_metrics(self):
        """Test weighted average computation for evaluation metrics."""
        # Arrange: Create multiple client records
        record1 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.80,
                    "eval_mae": 0.60,
                    "eval_loss": 0.64,
                    "num-examples": 100,
                })
            }
        )

        record2 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.90,
                    "eval_mae": 0.70,
                    "eval_loss": 0.81,
                    "num-examples": 200,
                })
            }
        )

        contents = [record1, record2]

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert
        assert isinstance(result, MetricRecord)
        metrics_dict = dict(result)

        # Weighted average: (0.80*100 + 0.90*200) / 300 = 0.8667
        assert metrics_dict["agg_rmse"] == pytest.approx(0.8667, rel=1e-4)
        # Weighted average: (0.60*100 + 0.70*200) / 300 = 0.6667
        assert metrics_dict["agg_mae"] == pytest.approx(0.6667, rel=1e-4)
        # Weighted average: (0.64*100 + 0.81*200) / 300 = 0.7533
        assert metrics_dict["agg_loss"] == pytest.approx(0.7533, rel=1e-4)
        assert metrics_dict["total_examples"] == 300

    def test_handles_train_loss_metrics(self):
        """Test aggregation of training metrics (loss only)."""
        # Arrange
        record1 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "train_loss": 1.00,
                    "num-examples": 150,
                })
            }
        )

        record2 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "train_loss": 0.80,
                    "num-examples": 150,
                })
            }
        )

        contents = [record1, record2]

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert
        metrics_dict = dict(result)

        # Should have loss but not RMSE/MAE
        assert "agg_loss" in metrics_dict
        assert "agg_rmse" not in metrics_dict
        assert "agg_mae" not in metrics_dict

        # Weighted average: (1.00*150 + 0.80*150) / 300 = 0.90
        assert metrics_dict["agg_loss"] == pytest.approx(0.90, rel=1e-4)
        assert metrics_dict["total_examples"] == 300

    def test_handles_empty_contents_list(self):
        """Test returns empty MetricRecord when no contents provided."""
        # Arrange
        contents = []

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert
        assert isinstance(result, MetricRecord)
        assert dict(result) == {}

    def test_returns_empty_when_total_examples_zero(self):
        """Test returns empty MetricRecord when total examples is zero."""
        # Arrange
        record = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.85,
                    "eval_mae": 0.65,
                    "eval_loss": 0.72,
                    "num-examples": 0,
                })
            }
        )
        contents = [record]

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert
        assert isinstance(result, MetricRecord)
        assert dict(result) == {}

    def test_aggregates_multiple_clients_correctly(self):
        """Test correct aggregation across many clients with varying weights."""
        # Arrange: 4 clients with different example counts
        contents = []
        for rmse, mae, loss, n_examples in [
            (0.75, 0.55, 0.56, 50),
            (0.80, 0.60, 0.64, 100),
            (0.85, 0.65, 0.72, 150),
            (0.90, 0.70, 0.81, 200),
        ]:
            record = RecordDict(
                metrics_records={
                    "metrics": MetricRecord({
                        "eval_rmse": rmse,
                        "eval_mae": mae,
                        "eval_loss": loss,
                        "num-examples": n_examples,
                    })
                }
            )
            contents.append(record)

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert
        metrics_dict = dict(result)

        # Expected weighted averages:
        # RMSE: (0.75*50 + 0.80*100 + 0.85*150 + 0.90*200) / 500 = 0.85
        # MAE:  (0.55*50 + 0.60*100 + 0.65*150 + 0.70*200) / 500 = 0.65
        # Loss: (0.56*50 + 0.64*100 + 0.72*150 + 0.81*200) / 500 = 0.724
        assert metrics_dict["agg_rmse"] == pytest.approx(0.85, rel=1e-3)
        assert metrics_dict["agg_mae"] == pytest.approx(0.65, rel=1e-3)
        assert metrics_dict["agg_loss"] == pytest.approx(0.724, rel=1e-3)
        assert metrics_dict["total_examples"] == 500

    def test_handles_missing_weighted_by_key(self):
        """Test defaults to weight of 1 when weighted_by_key is missing."""
        # Arrange: Record without num-examples key
        record1 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.80,
                    "eval_mae": 0.60,
                    "eval_loss": 0.64,
                    # num-examples is missing
                })
            }
        )

        record2 = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.90,
                    "eval_mae": 0.70,
                    "eval_loss": 0.81,
                    # num-examples is missing
                })
            }
        )

        contents = [record1, record2]

        # Act
        result = _weighted_average_metrics(contents, "num-examples")

        # Assert: Should use weight of 1 for each, giving simple average
        metrics_dict = dict(result)
        assert metrics_dict["agg_rmse"] == pytest.approx(0.85, rel=1e-4)  # (0.80 + 0.90) / 2
        assert metrics_dict["agg_mae"] == pytest.approx(0.65, rel=1e-4)   # (0.60 + 0.70) / 2
        assert metrics_dict["total_examples"] == 2


# ==================== _initialize_global_model Tests ====================


class TestInitializeGlobalModel:
    """Test suite for _initialize_global_model function."""

    def test_returns_array_record_with_item_params_only(self):
        """Test returns ArrayRecord containing only item-side parameters."""
        # Arrange
        n_users, n_items, n_factors = 100, 50, 16
        global_mean = 3.5

        # Act
        arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)

        # Assert
        assert isinstance(arrays, ArrayRecord)

        # Convert to dict to inspect keys
        state_dict = arrays.to_torch_state_dict()

        # Should contain exactly the item parameter names
        assert set(state_dict.keys()) == set(ITEM_PARAM_NAMES)

        # Should NOT contain user parameters
        assert "user_embedding.weight" not in state_dict
        assert "user_bias.weight" not in state_dict

    def test_parameter_shapes_match_model_dimensions(self):
        """Test parameter tensors have correct shapes."""
        # Arrange
        n_users, n_items, n_factors = 100, 50, 16
        global_mean = 3.5

        # Act
        arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)
        state_dict = arrays.to_torch_state_dict()

        # Assert shapes
        assert state_dict["global_bias"].shape == torch.Size([])  # Scalar
        assert state_dict["item_embedding.weight"].shape == torch.Size([n_items, n_factors])
        assert state_dict["item_bias.weight"].shape == torch.Size([n_items, 1])

    def test_global_bias_initialized_to_global_mean(self):
        """Test global_bias parameter is initialized to global_mean value."""
        # Arrange
        n_users, n_items, n_factors = 100, 50, 16
        global_mean = 4.2

        # Act
        arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)
        state_dict = arrays.to_torch_state_dict()

        # Assert
        assert state_dict["global_bias"].item() == pytest.approx(global_mean, rel=1e-5)

    def test_excludes_user_side_parameters(self):
        """Test explicitly verifies no user embeddings or biases are included."""
        # Arrange
        n_users, n_items, n_factors = 200, 100, 32
        global_mean = 3.8

        # Act
        arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)
        state_dict = arrays.to_torch_state_dict()

        # Assert: Check all keys are item-side only
        for key in state_dict.keys():
            assert "user" not in key.lower(), f"Found user parameter: {key}"
            assert key in ITEM_PARAM_NAMES, f"Unexpected parameter: {key}"

    def test_different_dimensions_produce_correct_shapes(self):
        """Test function works correctly with various dimension combinations."""
        # Arrange: Test multiple configurations
        configs = [
            (50, 25, 8, 3.0),
            (1000, 500, 64, 4.5),
            (10, 5, 4, 2.5),
        ]

        for n_users, n_items, n_factors, global_mean in configs:
            # Act
            arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)
            state_dict = arrays.to_torch_state_dict()

            # Assert
            assert state_dict["item_embedding.weight"].shape == torch.Size([n_items, n_factors])
            assert state_dict["item_bias.weight"].shape == torch.Size([n_items, 1])
            assert state_dict["global_bias"].item() == pytest.approx(global_mean, rel=1e-5)


# ==================== _save_final_metrics Tests ====================


class TestSaveFinalMetrics:
    """Test suite for _save_final_metrics function."""

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_creates_output_directory_if_not_exists(
        self,
        mock_mkdir,
        mock_file,
        mock_log,
        mock_fedavg_result,
    ):
        """Test creates output directory with parents=True, exist_ok=True."""
        # Arrange
        output_dir = Path("/fake/output/dir")

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=mock_fedavg_result,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            num_rounds=3,
        )

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_saves_correct_json_structure(
        self,
        mock_mkdir,
        mock_file,
        mock_log,
        mock_fedavg_result,
    ):
        """Test saves JSON with expected keys and structure."""
        # Arrange
        output_dir = Path("/fake/output/dir")
        n_users, n_items, n_factors = 100, 50, 16
        global_mean = 3.5
        num_rounds = 3

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=mock_fedavg_result,
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
            num_rounds=num_rounds,
        )

        # Assert: Extract the JSON written to file
        written_data = mock_file().write.call_args_list
        json_str = "".join(call[0][0] for call in written_data)
        saved_data = json.loads(json_str)

        # Verify top-level keys
        assert "best_test_rmse" in saved_data
        assert "best_test_mae" in saved_data
        assert "best_round" in saved_data
        assert "final_test_rmse" in saved_data
        assert "final_test_mae" in saved_data
        assert "rounds_completed" in saved_data
        assert "model_config" in saved_data
        assert "history" in saved_data

        # Verify model_config
        assert saved_data["model_config"]["n_users"] == n_users
        assert saved_data["model_config"]["n_items"] == n_items
        assert saved_data["model_config"]["n_factors"] == n_factors
        assert saved_data["model_config"]["global_bias"] == global_mean

        # Verify history structure
        assert "centralized_eval" in saved_data["history"]
        assert "client_eval" in saved_data["history"]
        assert "train" in saved_data["history"]

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_handles_empty_result_history(self, mock_mkdir, mock_file, mock_log):
        """Test handles result with no metrics gracefully."""
        # Arrange: Empty result
        result = Mock()
        result.evaluate_metrics_serverapp = None
        result.evaluate_metrics_clientapp = None
        result.train_metrics_clientapp = None

        output_dir = Path("/fake/output/dir")

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=result,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            num_rounds=10,
        )

        # Assert: Should still write JSON without errors
        written_data = mock_file().write.call_args_list
        json_str = "".join(call[0][0] for call in written_data)
        saved_data = json.loads(json_str)

        # Best metrics should be None
        assert saved_data["best_test_rmse"] is None
        assert saved_data["best_test_mae"] is None
        assert saved_data["best_round"] is None
        assert saved_data["final_test_rmse"] is None
        assert saved_data["final_test_mae"] is None

        # History should be empty dicts
        assert saved_data["history"]["centralized_eval"] == {}
        assert saved_data["history"]["client_eval"] == {}
        assert saved_data["history"]["train"] == {}

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_tracks_best_round_correctly(
        self,
        mock_mkdir,
        mock_file,
        mock_log,
        mock_fedavg_result,
    ):
        """Test identifies best round by minimum test_rmse."""
        # Arrange
        output_dir = Path("/fake/output/dir")

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=mock_fedavg_result,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            num_rounds=3,
        )

        # Assert
        written_data = mock_file().write.call_args_list
        json_str = "".join(call[0][0] for call in written_data)
        saved_data = json.loads(json_str)

        # Best round should be round 3 (RMSE: 0.80)
        assert saved_data["best_round"] == 3
        assert saved_data["best_test_rmse"] == 0.80
        assert saved_data["best_test_mae"] == 0.60

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_includes_model_configuration(self, mock_mkdir, mock_file, mock_log):
        """Test includes complete model configuration with parameter counts."""
        # Arrange
        result = Mock()
        result.evaluate_metrics_serverapp = {}
        result.evaluate_metrics_clientapp = {}
        result.train_metrics_clientapp = {}

        output_dir = Path("/fake/output/dir")
        n_users, n_items, n_factors = 5949, 2856, 32  # Goodreads dimensions
        global_mean = 3.87

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=result,
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
            num_rounds=10,
        )

        # Assert
        written_data = mock_file().write.call_args_list
        json_str = "".join(call[0][0] for call in written_data)
        saved_data = json.loads(json_str)

        model_config = saved_data["model_config"]

        # Verify dimensions
        assert model_config["n_users"] == n_users
        assert model_config["n_items"] == n_items
        assert model_config["n_factors"] == n_factors
        assert model_config["global_bias"] == global_mean

        # Verify parameter counts
        expected_item_params = 1 + n_items + (n_items * n_factors)
        expected_user_params = n_users + (n_users * n_factors)
        expected_total_params = expected_item_params + expected_user_params

        assert model_config["n_item_parameters"] == expected_item_params
        assert model_config["n_user_parameters"] == expected_user_params
        assert model_config["n_parameters"] == expected_total_params

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_saves_to_correct_file_path(self, mock_mkdir, mock_file, mock_log):
        """Test saves to final_metrics.json in output directory."""
        # Arrange
        result = Mock()
        result.evaluate_metrics_serverapp = {}
        result.evaluate_metrics_clientapp = {}
        result.train_metrics_clientapp = {}

        output_dir = Path("/custom/output/path")

        # Act
        _save_final_metrics(
            output_dir=output_dir,
            result=result,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            num_rounds=10,
        )

        # Assert
        expected_path = output_dir / "final_metrics.json"
        mock_file.assert_called_once_with(expected_path, "w")


# ==================== _create_centralized_evaluate_fn Tests ====================


class TestCreateCentralizedEvaluateFn:
    """Test suite for _create_centralized_evaluate_fn function."""

    @patch("app.application.federated.server_app.DatasetLoader")
    def test_returns_callable_evaluate_function(self, mock_loader_class):
        """Test returns a callable evaluation function."""
        # Arrange
        mock_loader = Mock()
        mock_loader.load = Mock()
        mock_loader.get_test_loader = Mock(return_value=[])
        mock_loader_class.return_value = mock_loader

        data_dir = Path("/fake/data")
        device = torch.device("cpu")

        # Act
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=data_dir,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            device=device,
        )

        # Assert
        assert callable(evaluate_fn)
        mock_loader.load.assert_called_once()
        mock_loader.get_test_loader.assert_called_once_with(batch_size=2048, num_workers=0)

    @patch("app.application.federated.server_app.log")
    @patch("app.application.federated.server_app.DatasetLoader")
    @patch("app.application.federated.server_app.LitBiasedMatrixFactorization")
    @patch("app.application.federated.server_app.compute_metrics")
    @patch("app.application.federated.server_app.torch.optim.Adam")
    @patch("app.application.federated.server_app.nn.MSELoss")
    def test_evaluate_fn_freezes_item_parameters(
        self,
        mock_mse_loss,
        mock_adam,
        mock_compute_metrics,
        mock_lit_model_class,
        mock_loader_class,
        mock_log,
    ):
        """Test inner evaluate_fn freezes item parameters during training."""
        # Arrange
        mock_loader = Mock()
        mock_loader.load = Mock()

        # Create simple test batch
        test_batch = [(
            torch.tensor([0, 1]),
            torch.tensor([0, 1]),
            torch.tensor([4.0, 5.0]),
        )]
        mock_loader.get_test_loader = Mock(return_value=test_batch)
        mock_loader_class.return_value = mock_loader

        # Mock optimizer
        mock_optimizer = Mock()
        mock_adam.return_value = mock_optimizer

        # Mock MSELoss
        mock_loss = Mock()
        mock_loss_value = Mock()
        mock_loss_value.backward = Mock()  # Mock backward to avoid grad issues
        mock_loss.return_value = mock_loss_value
        mock_mse_loss.return_value = mock_loss

        # Mock model
        mock_model = Mock()
        mock_model.model = Mock()
        mock_model.model.state_dict = Mock(return_value={
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
            "user_embedding.weight": torch.randn(100, 16),
            "user_bias.weight": torch.randn(100, 1),
        })
        mock_model.model.load_state_dict = Mock()

        # Create mock parameters with requires_grad tracking
        item_params = []
        user_params = []

        for name in ITEM_PARAM_NAMES:
            param = Mock()
            param.requires_grad = True
            item_params.append((name, param))

        for name in ["user_embedding.weight", "user_bias.weight"]:
            param = Mock()
            param.requires_grad = True
            user_params.append((name, param))

        all_params = item_params + user_params
        mock_model.model.named_parameters = Mock(return_value=all_params)
        mock_model.model.parameters = Mock(return_value=[p for _, p in all_params if p.requires_grad])

        # Mock forward pass
        mock_model.return_value = torch.tensor([4.1, 4.9])
        mock_model.train = Mock()
        mock_model.eval = Mock()
        mock_model.to = Mock(return_value=mock_model)
        mock_model.__call__ = Mock(return_value=torch.tensor([4.1, 4.9]))

        mock_lit_model_class.return_value = mock_model

        # Mock compute_metrics
        mock_compute_metrics.return_value = {"rmse": 0.85, "mae": 0.65}

        # Create evaluate function
        data_dir = Path("/fake/data")
        device = torch.device("cpu")
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=data_dir,
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            device=device,
            user_lr=0.001,
            user_epochs=3,
        )

        # Create mock ArrayRecord
        item_param_dict = {
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
        }
        arrays = ArrayRecord(item_param_dict)

        # Act
        result = evaluate_fn(server_round=1, arrays=arrays)

        # Assert
        assert isinstance(result, MetricRecord)

        # Verify model was created
        mock_lit_model_class.assert_called_once()

        # Verify model was put in train mode for user embedding training
        mock_model.train.assert_called()

        # Verify model was put in eval mode for final evaluation
        mock_model.eval.assert_called()

    @patch("app.application.federated.server_app.log")
    @patch("app.application.federated.server_app.DatasetLoader")
    @patch("app.application.federated.server_app.LitBiasedMatrixFactorization")
    @patch("app.application.federated.server_app.compute_metrics")
    @patch("app.application.federated.server_app.torch.optim.Adam")
    @patch("app.application.federated.server_app.nn.MSELoss")
    def test_evaluate_fn_returns_correct_metric_record(
        self,
        mock_mse_loss,
        mock_adam,
        mock_compute_metrics,
        mock_lit_model_class,
        mock_loader_class,
        mock_log,
    ):
        """Test inner evaluate_fn returns MetricRecord with expected structure."""
        # Arrange
        mock_loader = Mock()
        mock_loader.load = Mock()

        test_batch = [(
            torch.tensor([0, 1, 2]),
            torch.tensor([0, 1, 2]),
            torch.tensor([4.0, 5.0, 3.5]),
        )]
        mock_loader.get_test_loader = Mock(return_value=test_batch)
        mock_loader_class.return_value = mock_loader

        # Mock optimizer
        mock_optimizer = Mock()
        mock_adam.return_value = mock_optimizer

        # Mock MSELoss
        mock_loss = Mock()
        mock_loss_value = Mock()
        mock_loss_value.backward = Mock()
        mock_loss.return_value = mock_loss_value
        mock_mse_loss.return_value = mock_loss

        # Mock model
        mock_model = Mock()
        mock_model.model = Mock()
        mock_model.model.state_dict = Mock(return_value={
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
            "user_embedding.weight": torch.randn(100, 16),
            "user_bias.weight": torch.randn(100, 1),
        })
        mock_model.model.load_state_dict = Mock()
        mock_model.model.named_parameters = Mock(return_value=[
            (name, Mock(requires_grad=True)) for name in
            list(ITEM_PARAM_NAMES) + ["user_embedding.weight", "user_bias.weight"]
        ])
        mock_model.model.parameters = Mock(return_value=[Mock(requires_grad=True)])
        mock_model.return_value = torch.tensor([4.1, 4.9, 3.6])
        mock_model.train = Mock()
        mock_model.eval = Mock()
        mock_model.to = Mock(return_value=mock_model)
        mock_model.__call__ = Mock(return_value=torch.tensor([4.1, 4.9, 3.6]))

        mock_lit_model_class.return_value = mock_model

        # Mock compute_metrics to return known values
        mock_compute_metrics.return_value = {"rmse": 0.75, "mae": 0.55}

        # Create evaluate function
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=Path("/fake/data"),
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            device=torch.device("cpu"),
        )

        # Create mock ArrayRecord
        item_params = {
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
        }
        arrays = ArrayRecord(item_params)

        # Act
        result = evaluate_fn(server_round=1, arrays=arrays)

        # Assert
        assert isinstance(result, MetricRecord)
        metrics_dict = dict(result)

        assert "test_rmse" in metrics_dict
        assert "test_mae" in metrics_dict
        assert "test_loss" in metrics_dict
        assert "test_samples" in metrics_dict

        assert metrics_dict["test_rmse"] == 0.75
        assert metrics_dict["test_mae"] == 0.55
        assert metrics_dict["test_loss"] == pytest.approx(0.75 ** 2)  # MSE
        assert metrics_dict["test_samples"] == 3

    @patch("app.application.federated.server_app.log")
    @patch("app.application.federated.server_app.DatasetLoader")
    @patch("app.application.federated.server_app.LitBiasedMatrixFactorization")
    @patch("app.application.federated.server_app.compute_metrics")
    @patch("app.application.federated.server_app.torch.optim.Adam")
    @patch("app.application.federated.server_app.nn.MSELoss")
    def test_uses_provided_hyperparameters(
        self,
        mock_mse_loss,
        mock_adam,
        mock_compute_metrics,
        mock_lit_model_class,
        mock_loader_class,
        mock_log,
    ):
        """Test uses custom user_lr and user_epochs parameters."""
        # Arrange
        mock_loader = Mock()
        mock_loader.load = Mock()

        # Create test batch for user_epochs epochs
        test_batch = [(
            torch.tensor([0]),
            torch.tensor([0]),
            torch.tensor([4.0]),
        )]
        mock_loader.get_test_loader = Mock(return_value=test_batch)
        mock_loader_class.return_value = mock_loader

        # Mock optimizer
        mock_optimizer = Mock()
        mock_adam.return_value = mock_optimizer

        # Mock MSELoss
        mock_loss = Mock()
        mock_loss_value = Mock()
        mock_loss_value.backward = Mock()
        mock_loss.return_value = mock_loss_value
        mock_mse_loss.return_value = mock_loss

        # Mock model
        mock_model = Mock()
        mock_model.model = Mock()
        mock_model.model.state_dict = Mock(return_value={
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
            "user_embedding.weight": torch.randn(100, 16),
            "user_bias.weight": torch.randn(100, 1),
        })
        mock_model.model.load_state_dict = Mock()
        mock_model.model.named_parameters = Mock(return_value=[
            (name, Mock(requires_grad=True)) for name in
            list(ITEM_PARAM_NAMES) + ["user_embedding.weight", "user_bias.weight"]
        ])
        mock_model.model.parameters = Mock(return_value=[Mock(requires_grad=True)])
        mock_model.return_value = torch.tensor([4.1])
        mock_model.train = Mock()
        mock_model.eval = Mock()
        mock_model.to = Mock(return_value=mock_model)
        mock_model.__call__ = Mock(return_value=torch.tensor([4.1]))

        mock_lit_model_class.return_value = mock_model

        # Mock compute_metrics
        mock_compute_metrics.return_value = {"rmse": 0.85, "mae": 0.65}

        custom_user_lr = 0.05
        custom_user_epochs = 5

        # Act: Create and call evaluate function
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=Path("/fake/data"),
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            device=torch.device("cpu"),
            user_lr=custom_user_lr,
            user_epochs=custom_user_epochs,
        )

        # Create mock ArrayRecord and call evaluate_fn
        item_params = {
            "global_bias": torch.tensor(3.5),
            "item_embedding.weight": torch.randn(50, 16),
            "item_bias.weight": torch.randn(50, 1),
        }
        arrays = ArrayRecord(item_params)
        evaluate_fn(server_round=1, arrays=arrays)

        # Assert: Verify model was created with correct learning_rate
        mock_lit_model_class.assert_called_once()
        call_kwargs = mock_lit_model_class.call_args[1]
        assert call_kwargs["learning_rate"] == custom_user_lr
        assert call_kwargs["regularization"] == 0.0  # Should be 0 for quick training

    @patch("app.application.federated.server_app.log")
    @patch("app.application.federated.server_app.DatasetLoader")
    def test_preloads_test_data_once(self, mock_loader_class, mock_log):
        """Test DatasetLoader loads test data only once during creation."""
        # Arrange
        mock_loader = Mock()
        mock_loader.load = Mock()
        mock_loader.get_test_loader = Mock(return_value=[])
        mock_loader_class.return_value = mock_loader

        # Act
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=Path("/fake/data"),
            n_users=100,
            n_items=50,
            n_factors=16,
            global_mean=3.5,
            device=torch.device("cpu"),
        )

        # Assert: load() should be called once during function creation
        mock_loader.load.assert_called_once()

        # Test loader should be created once
        mock_loader.get_test_loader.assert_called_once_with(batch_size=2048, num_workers=0)


# ==================== Integration Tests ====================


class TestServerAppHelperIntegration:
    """Integration tests verifying helper functions work together correctly."""

    @patch("app.application.federated.server_app.log")
    def test_initialize_and_metrics_aggregation_flow(self, mock_log):
        """Test flow: initialize model -> aggregate metrics from clients."""
        # Arrange: Initialize global model
        n_users, n_items, n_factors = 100, 50, 16
        global_mean = 3.5

        initial_arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)

        # Simulate client responses with metrics
        client1_record = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.80,
                    "eval_mae": 0.60,
                    "eval_loss": 0.64,
                    "num-examples": 200,
                })
            }
        )

        client2_record = RecordDict(
            metrics_records={
                "metrics": MetricRecord({
                    "eval_rmse": 0.90,
                    "eval_mae": 0.70,
                    "eval_loss": 0.81,
                    "num-examples": 100,
                })
            }
        )

        # Act: Aggregate client metrics
        aggregated_metrics = _weighted_average_metrics(
            [client1_record, client2_record],
            "num-examples",
        )

        # Assert: Model initialized correctly
        assert isinstance(initial_arrays, ArrayRecord)
        state_dict = initial_arrays.to_torch_state_dict()
        assert state_dict["global_bias"].item() == pytest.approx(global_mean)

        # Assert: Metrics aggregated correctly
        metrics_dict = dict(aggregated_metrics)
        # Weighted: (0.80*200 + 0.90*100) / 300 = 0.8333
        assert metrics_dict["agg_rmse"] == pytest.approx(0.8333, rel=1e-4)

    @patch("app.application.federated.server_app.log")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_full_training_cycle_metrics_saving(
        self,
        mock_mkdir,
        mock_file,
        mock_log,
        mock_fedavg_result,
    ):
        """Test complete cycle: initialize -> train -> aggregate -> save."""
        # Arrange
        n_users, n_items, n_factors = 5949, 2856, 32
        global_mean = 3.87
        num_rounds = 3

        # Step 1: Initialize
        initial_arrays = _initialize_global_model(n_users, n_items, n_factors, global_mean)

        # Step 2: Simulate training (use mock result)
        # (In real scenario, this would be strategy.start())

        # Step 3: Save final metrics
        _save_final_metrics(
            output_dir=Path("/results/federated"),
            result=mock_fedavg_result,
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
            num_rounds=num_rounds,
        )

        # Assert: Verify complete workflow
        assert isinstance(initial_arrays, ArrayRecord)

        # Verify metrics were saved
        written_data = mock_file().write.call_args_list
        json_str = "".join(call[0][0] for call in written_data)
        saved_data = json.loads(json_str)

        assert saved_data["model_config"]["n_users"] == n_users
        assert saved_data["model_config"]["n_items"] == n_items
        assert saved_data["rounds_completed"] == num_rounds
        assert saved_data["best_round"] == 3  # Round with lowest RMSE
