"""Integration tests for ExperimentManager.

Tests cover:
- End-to-end experiment execution with mocked services
- Data loading and training integration
- Metrics persistence flow

Note: These tests use mocked services to avoid database dependencies.
Full integration tests with real database should be in a separate test suite.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment
from app.utils.types import ExperimentStatus


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_experiment_service() -> AsyncMock:
    """Create a mocked ExperimentService."""
    service = AsyncMock(spec=ExperimentService)

    # Configure create_centralized_experiment to return a valid experiment
    async def create_experiment(name: str, config: Configuration):
        return CentralizedExperiment(
            experiment_id="test-exp-123",
            name=name,
            config=config,
            status=ExperimentStatus.PENDING,
        )

    service.create_centralized_experiment = AsyncMock(side_effect=create_experiment)

    # Configure start_experiment to return the experiment in RUNNING state
    async def start_experiment(experiment_id: str):
        config = Configuration(n_factors=8, n_epochs=2)
        exp = CentralizedExperiment(
            experiment_id=experiment_id,
            name="Test",
            config=config,
            status=ExperimentStatus.PENDING,
        )
        exp.mark_running()
        return exp

    service.start_experiment = AsyncMock(side_effect=start_experiment)

    # Configure complete_experiment
    async def complete_experiment(
        experiment_id: str,
        final_rmse: float,
        final_mae: float,
        training_time_seconds: float,
    ):
        config = Configuration(n_factors=8, n_epochs=2)
        from app.core.metrics import ExperimentMetrics

        exp = CentralizedExperiment(
            experiment_id=experiment_id,
            name="Test",
            config=config,
            status=ExperimentStatus.RUNNING,
        )
        exp.mark_completed(
            ExperimentMetrics(
                rmse=final_rmse,
                mae=final_mae,
                training_time_seconds=training_time_seconds,
            )
        )
        return exp

    service.complete_experiment = AsyncMock(side_effect=complete_experiment)

    # Configure fail_experiment
    service.fail_experiment = AsyncMock()

    return service


@pytest.fixture
def mock_metrics_service() -> AsyncMock:
    """Create a mocked MetricsService."""
    service = AsyncMock(spec=MetricsService)
    service.add_metrics_batch = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_data_loader() -> MagicMock:
    """Create a mocked DatasetLoader with synthetic data."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset

    # Create synthetic data
    n_samples = 200
    n_users = 50
    n_items = 30

    user_ids = torch.randint(0, n_users, (n_samples,))
    item_ids = torch.randint(0, n_items, (n_samples,))
    ratings = torch.rand(n_samples) * 4 + 1

    dataset = TensorDataset(user_ids, item_ids, ratings)

    loader = MagicMock()
    loader.load = MagicMock()
    loader.n_users = n_users
    loader.n_items = n_items
    loader.global_mean = 3.5
    loader.get_train_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=True)
    )
    loader.get_val_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=False)
    )
    loader.get_metadata = MagicMock(
        return_value=MagicMock(
            n_users=n_users,
            n_items=n_items,
            global_mean=3.5,
            train_size=n_samples,
            val_size=n_samples // 5,
            test_size=n_samples // 5,
            sparsity=0.95,
        )
    )

    return loader


@pytest.fixture
def experiment_manager(
    mock_experiment_service: AsyncMock,
    mock_metrics_service: AsyncMock,
) -> ExperimentManager:
    """Create ExperimentManager with mocked services."""
    return ExperimentManager(
        experiment_service=mock_experiment_service,
        metrics_service=mock_metrics_service,
        data_dir=Path("data"),  # Won't be used due to mocked data loader
        batch_size=64,
    )


# -----------------------------------------------------------------------------
# ExperimentManager Tests
# -----------------------------------------------------------------------------


class TestExperimentManagerInitialization:
    """Tests for ExperimentManager initialization."""

    def test_initialization_stores_services(
        self,
        mock_experiment_service: AsyncMock,
        mock_metrics_service: AsyncMock,
    ) -> None:
        """Manager stores service references."""
        manager = ExperimentManager(
            experiment_service=mock_experiment_service,
            metrics_service=mock_metrics_service,
            data_dir=Path("data"),
        )

        assert manager._experiment_service is mock_experiment_service
        assert manager._metrics_service is mock_metrics_service
        assert manager._data_dir == Path("data")


class TestCentralizedExperimentExecution:
    """Tests for centralized experiment execution."""

    @pytest.mark.asyncio
    async def test_run_centralized_experiment_creates_experiment(
        self,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
        mock_data_loader: MagicMock,
    ) -> None:
        """run_centralized_experiment creates experiment via service."""
        config = Configuration(n_factors=8, n_epochs=2)

        # Patch DatasetLoader to use our mock
        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=mock_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Test Experiment",
                config=config,
                accelerator="cpu",
            )

        # Verify experiment was created
        mock_experiment_service.create_centralized_experiment.assert_called_once_with(
            name="Test Experiment",
            config=config,
        )

        # Verify experiment was started
        mock_experiment_service.start_experiment.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_centralized_experiment_completes_experiment(
        self,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
        mock_data_loader: MagicMock,
    ) -> None:
        """run_centralized_experiment completes experiment with metrics."""
        config = Configuration(n_factors=8, n_epochs=2)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=mock_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Test Experiment",
                config=config,
                accelerator="cpu",
            )

        # Verify experiment was completed
        mock_experiment_service.complete_experiment.assert_called_once()
        call_args = mock_experiment_service.complete_experiment.call_args
        assert call_args.kwargs["experiment_id"] == "test-exp-123"
        assert "final_rmse" in call_args.kwargs
        assert "final_mae" in call_args.kwargs
        assert "training_time_seconds" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_run_centralized_experiment_persists_metrics(
        self,
        experiment_manager: ExperimentManager,
        mock_metrics_service: AsyncMock,
        mock_data_loader: MagicMock,
    ) -> None:
        """run_centralized_experiment persists per-epoch metrics."""
        config = Configuration(n_factors=8, n_epochs=2)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=mock_data_loader
        ):
            await experiment_manager.run_centralized_experiment(
                name="Test Experiment",
                config=config,
                accelerator="cpu",
            )

        # Verify metrics were persisted
        mock_metrics_service.add_metrics_batch.assert_called_once()
        call_args = mock_metrics_service.add_metrics_batch.call_args
        assert call_args.kwargs["experiment_id"] == "test-exp-123"

        # Should have multiple metrics (loss, rmse, mae for each epoch)
        metrics = call_args.kwargs["metrics"]
        assert len(metrics) > 0

        # Check metric types
        metric_names = {m.name for m in metrics}
        assert "loss" in metric_names
        assert "rmse" in metric_names

    @pytest.mark.asyncio
    async def test_run_centralized_experiment_returns_completed_experiment(
        self,
        experiment_manager: ExperimentManager,
        mock_data_loader: MagicMock,
    ) -> None:
        """run_centralized_experiment returns completed experiment."""
        config = Configuration(n_factors=8, n_epochs=2)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=mock_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Test Experiment",
                config=config,
                accelerator="cpu",
            )

        assert isinstance(result, CentralizedExperiment)
        assert result.status == ExperimentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_centralized_experiment_fails_gracefully(
        self,
        experiment_manager: ExperimentManager,
        mock_experiment_service: AsyncMock,
        mock_data_loader: MagicMock,
    ) -> None:
        """run_centralized_experiment marks experiment as failed on error."""
        config = Configuration(n_factors=8, n_epochs=2)

        # Make training fail
        mock_data_loader.get_train_loader.side_effect = RuntimeError("Data error")

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=mock_data_loader
        ):
            with pytest.raises(RuntimeError, match="Data error"):
                await experiment_manager.run_centralized_experiment(
                    name="Test Experiment",
                    config=config,
                    accelerator="cpu",
                )

        # Verify experiment was marked as failed
        mock_experiment_service.fail_experiment.assert_called_once_with("test-exp-123")


class TestDataMetadata:
    """Tests for data metadata property."""

    def test_data_metadata_returns_none_before_loading(
        self,
        experiment_manager: ExperimentManager,
    ) -> None:
        """data_metadata returns None before data is loaded."""
        assert experiment_manager.data_metadata is None

    def test_data_metadata_returns_info_after_loading(
        self,
        experiment_manager: ExperimentManager,
        mock_data_loader: MagicMock,
    ) -> None:
        """data_metadata returns dataset info after loading."""
        experiment_manager._data_loader = mock_data_loader

        metadata = experiment_manager.data_metadata

        assert metadata is not None
        assert metadata["n_users"] == 50
        assert metadata["n_items"] == 30
        assert metadata["global_mean"] == 3.5
