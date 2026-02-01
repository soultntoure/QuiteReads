"""Unit tests for ExperimentManager federated experiment path.

Tests cover:
- run_federated_experiment() lifecycle
- _persist_federated_metrics() database persistence
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.experiment_manager import ExperimentManager
from app.application.training.federated_simulation_manager import (
    FederatedSimulationResult,
)
from app.core.configuration import AggregationStrategy, Configuration
from app.core.experiments import ExperimentStatus
from app.core.metrics import PerformanceMetric


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
            {
                "round": 1,
                "test_rmse": 1.2,
                "test_mae": 0.9,
                "test_loss": 1.44,
                "client_eval_rmse": 1.3,
                "client_eval_mae": 0.95,
                "train_loss": 0.5,
            },
            {
                "round": 2,
                "test_rmse": 1.1,
                "test_mae": 0.85,
                "test_loss": 1.21,
                "train_loss": 0.4,
            },
            {
                "round": 3,
                "test_rmse": 1.0,
                "test_mae": 0.8,
                "test_loss": 1.0,
                "train_loss": 0.35,
            },
        ],
    )


@pytest.fixture
def empty_metrics_result() -> FederatedSimulationResult:
    """Result with empty metrics_by_round."""
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
def mock_experiment_service() -> AsyncMock:
    """Mock ExperimentService."""
    service = AsyncMock()
    
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = str(uuid4())
    mock_experiment.status = ExperimentStatus.PENDING
    
    service.create_federated_experiment.return_value = mock_experiment
    service.start_experiment.return_value = None
    service.complete_experiment.return_value = mock_experiment
    service.fail_experiment.return_value = None
    
    return service


@pytest.fixture
def mock_metrics_service() -> AsyncMock:
    """Mock MetricsService."""
    service = AsyncMock()
    service.add_metrics_batch.return_value = None
    return service


@pytest.fixture
def experiment_manager(
    mock_experiment_service: AsyncMock,
    mock_metrics_service: AsyncMock,
    tmp_path,
) -> ExperimentManager:
    """ExperimentManager with mocked services."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return ExperimentManager(
        experiment_service=mock_experiment_service,
        metrics_service=mock_metrics_service,
        data_dir=data_dir,
        storage_dir=tmp_path / "storage",
    )


@pytest.fixture
def mock_config() -> Configuration:
    """Mock Configuration with default values."""
    return Configuration(
        n_factors=16,
        learning_rate=0.01,
        regularization=0.001,
        n_epochs=10,
        random_seed=42,
    )


# -----------------------------------------------------------------------------
# run_federated_experiment Lifecycle Tests
# -----------------------------------------------------------------------------


class TestRunFederatedExperimentLifecycle:
    """Tests for run_federated_experiment experiment lifecycle."""

    @pytest.mark.asyncio
    @patch("app.application.experiment_manager.FederatedSimulationManager")
    async def test_creates_experiment_and_transitions_to_running(
        self,
        mock_sim_manager_class: MagicMock,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Creates experiment via service and transitions to RUNNING."""
        mock_sim_manager = MagicMock()
        mock_sim_manager.run_simulation.return_value = sample_simulation_result
        mock_sim_manager_class.return_value = mock_sim_manager

        await experiment_manager.run_federated_experiment(
            name="test_fed_exp",
            config=Configuration(n_factors=16),
            n_clients=5,
            n_rounds=3,
        )

        mock_experiment_service.create_federated_experiment.assert_called_once()
        mock_experiment_service.start_experiment.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.application.experiment_manager.FederatedSimulationManager")
    async def test_calls_simulation_manager_with_correct_params(
        self,
        mock_sim_manager_class: MagicMock,
        experiment_manager: ExperimentManager,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Calls FederatedSimulationManager.run_simulation with correct params."""
        mock_sim_manager = MagicMock()
        mock_sim_manager.run_simulation.return_value = sample_simulation_result
        mock_sim_manager_class.return_value = mock_sim_manager

        await experiment_manager.run_federated_experiment(
            name="test_fed_exp",
            config=Configuration(n_factors=32),
            n_clients=5,
            n_rounds=10,
        )

        mock_sim_manager.run_simulation.assert_called_once()
        call_kwargs = mock_sim_manager.run_simulation.call_args[1]
        assert call_kwargs["num_rounds"] == 10
        assert call_kwargs["n_factors"] == 32

    @pytest.mark.asyncio
    @patch("app.application.experiment_manager.FederatedSimulationManager")
    async def test_transitions_to_completed_with_final_metrics(
        self,
        mock_sim_manager_class: MagicMock,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Transitions to COMPLETED with final_rmse and final_mae."""
        mock_sim_manager = MagicMock()
        mock_sim_manager.run_simulation.return_value = sample_simulation_result
        mock_sim_manager_class.return_value = mock_sim_manager

        await experiment_manager.run_federated_experiment(
            name="test_fed_exp",
            config=Configuration(n_factors=16),
            n_clients=5,
            n_rounds=3,
        )

        mock_experiment_service.complete_experiment.assert_called_once()
        call_kwargs = mock_experiment_service.complete_experiment.call_args[1]
        assert call_kwargs["final_rmse"] == 1.0
        assert call_kwargs["final_mae"] == 0.8

    @pytest.mark.asyncio
    @patch("app.application.experiment_manager.FederatedSimulationManager")
    async def test_failure_path_calls_fail_experiment(
        self,
        mock_sim_manager_class: MagicMock,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
    ) -> None:
        """Exception during simulation calls fail_experiment."""
        mock_sim_manager = MagicMock()
        mock_sim_manager.run_simulation.side_effect = RuntimeError("Simulation failed")
        mock_sim_manager_class.return_value = mock_sim_manager

        with pytest.raises(RuntimeError):
            await experiment_manager.run_federated_experiment(
                name="test_fed_exp",
                config=Configuration(n_factors=16),
                n_clients=5,
                n_rounds=3,
            )

        mock_experiment_service.fail_experiment.assert_called_once()


# -----------------------------------------------------------------------------
# _persist_federated_metrics Tests
# -----------------------------------------------------------------------------


class TestPersistFederatedMetrics:
    """Tests for _persist_federated_metrics database persistence."""

    @pytest.mark.asyncio
    async def test_converts_centralized_test_metrics(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Converts test_rmse, test_mae, test_loss with context='centralized_test'."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, sample_simulation_result
        )

        mock_metrics_service.add_metrics_batch.assert_called_once()
        call_args = mock_metrics_service.add_metrics_batch.call_args
        metrics = call_args[1]["metrics"]

        # Find centralized_test metrics
        centralized_metrics = [m for m in metrics if m.context == "centralized_test"]
        assert len(centralized_metrics) > 0

        # Check RMSE metrics exist for each round
        rmse_metrics = [m for m in centralized_metrics if m.name == "rmse"]
        assert len(rmse_metrics) == 3  # 3 rounds

    @pytest.mark.asyncio
    async def test_converts_client_aggregated_metrics(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Converts client_eval_rmse, client_eval_mae with context='client_aggregated'."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, sample_simulation_result
        )

        call_args = mock_metrics_service.add_metrics_batch.call_args
        metrics = call_args[1]["metrics"]

        # Find client_aggregated metrics
        client_metrics = [m for m in metrics if m.context == "client_aggregated"]
        # Round 1 has client_eval_rmse and client_eval_mae
        assert len(client_metrics) >= 2

    @pytest.mark.asyncio
    async def test_converts_training_metrics(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Converts train_loss with context='training'."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, sample_simulation_result
        )

        call_args = mock_metrics_service.add_metrics_batch.call_args
        metrics = call_args[1]["metrics"]

        # Find training metrics
        training_metrics = [m for m in metrics if m.context == "training"]
        assert len(training_metrics) == 3  # 3 rounds of train_loss

    @pytest.mark.asyncio
    async def test_metrics_have_correct_round_number(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """All metrics have correct round_number field."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, sample_simulation_result
        )

        call_args = mock_metrics_service.add_metrics_batch.call_args
        metrics = call_args[1]["metrics"]

        # Check round numbers are 1, 2, 3
        round_numbers = set(m.round_number for m in metrics)
        assert round_numbers == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_calls_add_metrics_batch_with_experiment_id(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        sample_simulation_result: FederatedSimulationResult,
    ) -> None:
        """Calls add_metrics_batch with correct experiment_id."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, sample_simulation_result
        )

        call_args = mock_metrics_service.add_metrics_batch.call_args
        assert call_args[1]["experiment_id"] == experiment_id

    @pytest.mark.asyncio
    async def test_handles_empty_metrics_by_round(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        empty_metrics_result: FederatedSimulationResult,
    ) -> None:
        """Handles empty metrics_by_round gracefully."""
        experiment_id = str(uuid4())

        await experiment_manager._persist_federated_metrics(
            experiment_id, empty_metrics_result
        )

        # Should not call add_metrics_batch with empty list
        mock_metrics_service.add_metrics_batch.assert_not_called()
