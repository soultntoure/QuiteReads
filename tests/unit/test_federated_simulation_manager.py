"""Unit tests for FederatedSimulationManager orchestration.

Tests cover:
- FederatedSimulationResult dataclass properties
- _build_run_config() parameter propagation
- _extract_metrics_from_result() metric extraction
- run_simulation() metric calculation logic
- _partition_data() caching behavior
"""

from collections import OrderedDict
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.application.training.federated_simulation_manager import (
    FederatedSimulationManager,
    FederatedSimulationResult,
)
from app.utils.exceptions import FederatedSimulationError


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def sample_simulation_result() -> FederatedSimulationResult:
    """Sample FederatedSimulationResult for testing."""
    return FederatedSimulationResult(
        final_rmse=1.0,
        final_mae=0.8,
        best_rmse=0.95,
        best_mae=0.75,
        best_round=2,
        training_time_seconds=120.0,
        num_rounds=3,
        metrics_by_round=[
            {"round": 1, "test_rmse": 1.2, "test_mae": 0.9, "train_loss": 0.5},
            {"round": 2, "test_rmse": 0.95, "test_mae": 0.75, "train_loss": 0.4},
            {"round": 3, "test_rmse": 1.0, "test_mae": 0.8, "train_loss": 0.35},
        ],
    )


@pytest.fixture
def empty_result() -> FederatedSimulationResult:
    """FederatedSimulationResult with empty metrics_by_round."""
    return FederatedSimulationResult(
        final_rmse=1.0,
        final_mae=0.8,
        best_rmse=1.0,
        best_mae=0.8,
        best_round=1,
        training_time_seconds=10.0,
        num_rounds=1,
        metrics_by_round=[],
    )


@pytest.fixture
def mock_flower_history() -> MagicMock:
    """Mock Flower History object with typical metrics."""
    history = MagicMock()
    history.metrics_centralized = {
        "test_rmse": [(1, 1.2), (2, 1.1), (3, 1.0)],
        "test_mae": [(1, 0.9), (2, 0.85), (3, 0.8)],
        "test_loss": [(1, 1.44), (2, 1.21), (3, 1.0)],
    }
    history.metrics_distributed = {
        "eval_rmse": [(1, 1.3), (2, 1.2), (3, 1.1)],
        "eval_mae": [(1, 0.95), (2, 0.9), (3, 0.85)],
    }
    history.losses_distributed = [(1, 0.5), (2, 0.4), (3, 0.35)]
    return history


@pytest.fixture
def partial_history() -> MagicMock:
    """History with only centralized metrics (no distributed)."""
    history = MagicMock()
    history.metrics_centralized = {
        "test_rmse": [(1, 1.0)],
        "test_mae": [(1, 0.8)],
    }
    history.metrics_distributed = {}
    history.losses_distributed = []
    return history


@pytest.fixture
def empty_history() -> MagicMock:
    """Empty History object."""
    history = MagicMock()
    history.metrics_centralized = {}
    history.metrics_distributed = {}
    history.losses_distributed = []
    return history


@pytest.fixture
def simulation_manager(tmp_path: Path) -> FederatedSimulationManager:
    """FederatedSimulationManager with temp directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return FederatedSimulationManager(
        data_dir=data_dir,
        storage_dir=storage_dir,
        num_clients=5,
        random_seed=42,
    )


# -----------------------------------------------------------------------------
# FederatedSimulationResult Tests
# -----------------------------------------------------------------------------


class TestFederatedSimulationResult:
    """Tests for FederatedSimulationResult dataclass."""

    def test_initialization_with_all_fields(
        self, sample_simulation_result: FederatedSimulationResult
    ) -> None:
        """Result initializes with all fields correctly."""
        assert sample_simulation_result.final_rmse == 1.0
        assert sample_simulation_result.final_mae == 0.8
        assert sample_simulation_result.best_rmse == 0.95
        assert sample_simulation_result.best_mae == 0.75
        assert sample_simulation_result.best_round == 2
        assert sample_simulation_result.training_time_seconds == 120.0
        assert sample_simulation_result.num_rounds == 3
        assert len(sample_simulation_result.metrics_by_round) == 3

    def test_converged_rmse_returns_final_rmse(
        self, sample_simulation_result: FederatedSimulationResult
    ) -> None:
        """converged_rmse property returns final_rmse."""
        assert sample_simulation_result.converged_rmse == 1.0

    def test_improvement_over_rounds_calculates_difference(
        self, sample_simulation_result: FederatedSimulationResult
    ) -> None:
        """improvement_over_rounds calculates first - final RMSE."""
        # First round test_rmse: 1.2, final: 1.0 -> improvement: 0.2
        assert sample_simulation_result.improvement_over_rounds == pytest.approx(0.2)

    def test_improvement_over_rounds_handles_empty_metrics(
        self, empty_result: FederatedSimulationResult
    ) -> None:
        """improvement_over_rounds returns 0.0 for empty metrics_by_round."""
        assert empty_result.improvement_over_rounds == 0.0


# -----------------------------------------------------------------------------
# _build_run_config Tests
# -----------------------------------------------------------------------------


class TestBuildRunConfig:
    """Tests for _build_run_config method."""

    def test_basic_parameters_propagate(
        self, simulation_manager: FederatedSimulationManager, tmp_path: Path
    ) -> None:
        """Basic training parameters propagate correctly."""
        partition_dir = tmp_path / "partitions"
        config = simulation_manager._build_run_config(
            partition_dir=partition_dir,
            num_rounds=10,
            n_factors=32,
            learning_rate=0.01,
            regularization=0.001,
            local_epochs=3,
            batch_size=512,
        )
        assert config["num-rounds"] == 10
        assert config["n-factors"] == 32
        assert config["learning-rate"] == 0.01
        assert config["regularization"] == 0.001
        assert config["local-epochs"] == 3
        assert config["batch-size"] == 512

    def test_client_selection_parameters(
        self, simulation_manager: FederatedSimulationManager, tmp_path: Path
    ) -> None:
        """Client selection parameters propagate correctly."""
        partition_dir = tmp_path / "partitions"
        config = simulation_manager._build_run_config(
            partition_dir=partition_dir,
            num_rounds=5,
            n_factors=16,
            fraction_train=0.8,
            fraction_evaluate=0.5,
        )
        assert config["fraction-train"] == 0.8
        assert config["fraction-evaluate"] == 0.5
        # min-clients should be min(2, num_clients=5) = 2
        assert config["min-train-clients"] == 2
        assert config["min-evaluate-clients"] == 2

    def test_centralized_eval_parameters(
        self, simulation_manager: FederatedSimulationManager, tmp_path: Path
    ) -> None:
        """Centralized evaluation parameters propagate correctly."""
        partition_dir = tmp_path / "partitions"
        config = simulation_manager._build_run_config(
            partition_dir=partition_dir,
            num_rounds=5,
            n_factors=16,
            enable_centralized_eval=True,
            user_lr=0.05,
            user_epochs=5,
        )
        assert config["centralized-eval"] is True
        assert config["user-lr"] == 0.05
        assert config["user-epochs"] == 5

    def test_paths_serialized_as_strings(
        self, simulation_manager: FederatedSimulationManager, tmp_path: Path
    ) -> None:
        """Path objects are serialized as strings in config."""
        partition_dir = tmp_path / "partitions"
        config = simulation_manager._build_run_config(
            partition_dir=partition_dir,
            num_rounds=5,
            n_factors=16,
        )
        assert isinstance(config["data-dir"], str)
        assert isinstance(config["partition-dir"], str)
        assert isinstance(config["output-dir"], str)


# -----------------------------------------------------------------------------
# _extract_metrics_from_result Tests
# -----------------------------------------------------------------------------


class TestExtractMetricsFromResult:
    """Tests for _extract_metrics_from_result method."""

    def test_extracts_centralized_metrics(
        self,
        simulation_manager: FederatedSimulationManager,
        mock_flower_history: MagicMock,
    ) -> None:
        """Extracts centralized test metrics correctly."""
        metrics = simulation_manager._extract_metrics_from_result(
            mock_flower_history, num_rounds=3
        )
        assert len(metrics) == 3
        assert metrics[0]["test_rmse"] == 1.2
        assert metrics[1]["test_rmse"] == 1.1
        assert metrics[2]["test_rmse"] == 1.0

    def test_extracts_distributed_client_metrics(
        self,
        simulation_manager: FederatedSimulationManager,
        mock_flower_history: MagicMock,
    ) -> None:
        """Extracts distributed client evaluation metrics."""
        metrics = simulation_manager._extract_metrics_from_result(
            mock_flower_history, num_rounds=3
        )
        assert metrics[0]["client_eval_rmse"] == 1.3
        assert metrics[0]["client_eval_mae"] == 0.95

    def test_extracts_training_losses(
        self,
        simulation_manager: FederatedSimulationManager,
        mock_flower_history: MagicMock,
    ) -> None:
        """Extracts training losses from losses_distributed."""
        metrics = simulation_manager._extract_metrics_from_result(
            mock_flower_history, num_rounds=3
        )
        assert metrics[0]["train_loss"] == 0.5
        assert metrics[2]["train_loss"] == 0.35

    def test_handles_partial_history(
        self,
        simulation_manager: FederatedSimulationManager,
        partial_history: MagicMock,
    ) -> None:
        """Handles History with partial metrics gracefully."""
        metrics = simulation_manager._extract_metrics_from_result(
            partial_history, num_rounds=1
        )
        assert metrics[0]["test_rmse"] == 1.0
        assert metrics[0].get("client_eval_rmse") is None
        assert metrics[0].get("train_loss") is None

    def test_handles_empty_history(
        self,
        simulation_manager: FederatedSimulationManager,
        empty_history: MagicMock,
    ) -> None:
        """Handles empty History object gracefully."""
        metrics = simulation_manager._extract_metrics_from_result(
            empty_history, num_rounds=2
        )
        assert len(metrics) == 2
        assert metrics[0].get("test_rmse") is None

    def test_produces_correct_round_count(
        self,
        simulation_manager: FederatedSimulationManager,
        mock_flower_history: MagicMock,
    ) -> None:
        """Produces correct number of round entries."""
        metrics = simulation_manager._extract_metrics_from_result(
            mock_flower_history, num_rounds=3
        )
        assert len(metrics) == 3
        assert metrics[0]["round"] == 1
        assert metrics[1]["round"] == 2
        assert metrics[2]["round"] == 3


# -----------------------------------------------------------------------------
# run_simulation Metric Logic Tests
# -----------------------------------------------------------------------------


class TestRunSimulationMetricLogic:
    """Tests for run_simulation metric calculation logic (with mocked simulation)."""

    @patch.object(FederatedSimulationManager, "_partition_data")
    @patch.object(FederatedSimulationManager, "_run_flower_simulation")
    def test_calculates_final_best_rmse_from_centralized(
        self,
        mock_run_sim: MagicMock,
        mock_partition: MagicMock,
        simulation_manager: FederatedSimulationManager,
        mock_flower_history: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Calculates final/best RMSE from centralized metrics."""
        mock_partition.return_value = tmp_path / "partitions"
        mock_run_sim.return_value = mock_flower_history

        result = simulation_manager.run_simulation(num_rounds=3, n_factors=16)

        # Final is from last round: 1.0
        assert result.final_rmse == 1.0
        # Best is minimum: 1.0 (round 3)
        assert result.best_rmse == 1.0
        assert result.best_round == 3

    @patch.object(FederatedSimulationManager, "_partition_data")
    @patch.object(FederatedSimulationManager, "_run_flower_simulation")
    def test_fallback_to_client_metrics_when_no_centralized(
        self,
        mock_run_sim: MagicMock,
        mock_partition: MagicMock,
        simulation_manager: FederatedSimulationManager,
        tmp_path: Path,
    ) -> None:
        """Falls back to client-side metrics when centralized eval disabled."""
        mock_partition.return_value = tmp_path / "partitions"
        
        # History with only distributed metrics (no centralized)
        history = MagicMock()
        history.metrics_centralized = {}
        history.metrics_distributed = {
            "eval_rmse": [(1, 1.5), (2, 1.3)],
            "eval_mae": [(1, 1.0), (2, 0.9)],
        }
        history.losses_distributed = []
        mock_run_sim.return_value = history

        result = simulation_manager.run_simulation(
            num_rounds=2, n_factors=16, enable_centralized_eval=False
        )

        assert result.final_rmse == 1.3
        assert result.best_rmse == 1.3
        assert result.best_round == 2

    @patch.object(FederatedSimulationManager, "_partition_data")
    @patch.object(FederatedSimulationManager, "_run_flower_simulation")
    def test_raises_error_when_no_metrics_produced(
        self,
        mock_run_sim: MagicMock,
        mock_partition: MagicMock,
        simulation_manager: FederatedSimulationManager,
        empty_history: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Raises FederatedSimulationError when no metrics produced."""
        mock_partition.return_value = tmp_path / "partitions"
        mock_run_sim.return_value = empty_history

        with pytest.raises(FederatedSimulationError) as exc_info:
            simulation_manager.run_simulation(num_rounds=2, n_factors=16)
        
        assert "No evaluation metrics" in str(exc_info.value)

    @patch.object(FederatedSimulationManager, "_partition_data")
    @patch.object(FederatedSimulationManager, "_run_flower_simulation")
    def test_tracks_best_round_correctly(
        self,
        mock_run_sim: MagicMock,
        mock_partition: MagicMock,
        simulation_manager: FederatedSimulationManager,
        tmp_path: Path,
    ) -> None:
        """Best round tracks the round with minimum RMSE."""
        mock_partition.return_value = tmp_path / "partitions"
        
        history = MagicMock()
        history.metrics_centralized = {
            "test_rmse": [(1, 1.5), (2, 1.0), (3, 1.2)],  # Best at round 2
            "test_mae": [(1, 1.0), (2, 0.8), (3, 0.9)],
        }
        history.metrics_distributed = {}
        history.losses_distributed = []
        mock_run_sim.return_value = history

        result = simulation_manager.run_simulation(num_rounds=3, n_factors=16)

        assert result.best_round == 2
        assert result.best_rmse == 1.0


# -----------------------------------------------------------------------------
# _partition_data Caching Tests
# -----------------------------------------------------------------------------


class TestPartitionDataCaching:
    """Tests for _partition_data caching behavior."""

    def test_skips_repartition_when_config_exists(
        self, simulation_manager: FederatedSimulationManager
    ) -> None:
        """Skips re-partitioning when partition_config.json exists."""
        partition_dir = simulation_manager.storage_dir / "partitions"
        partition_dir.mkdir(parents=True)
        (partition_dir / "partition_config.json").write_text("{}")

        result = simulation_manager._partition_data(force=False)

        # Should return existing partition dir without calling partitioner
        assert result == partition_dir

    def test_repartitions_when_force_true(
        self, simulation_manager: FederatedSimulationManager
    ) -> None:
        """Re-partitions when force=True even if config exists."""
        partition_dir = simulation_manager.storage_dir / "partitions"
        partition_dir.mkdir(parents=True)
        (partition_dir / "partition_config.json").write_text("{}")

        with patch(
            "app.application.training.federated_simulation_manager.UserPartitioner"
        ) as mock_partitioner:
            mock_instance = MagicMock()
            mock_partitioner.return_value = mock_instance
            mock_instance.partition.return_value = partition_dir

            result = simulation_manager._partition_data(force=True)

            # Partitioner should be called
            mock_partitioner.assert_called_once()
            mock_instance.partition.assert_called_once()
