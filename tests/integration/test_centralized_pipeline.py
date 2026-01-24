"""Integration tests for centralized training pipeline.

Tests end-to-end flow from ExperimentManager through to database persistence.
Uses real services with in-memory SQLite database to verify:
- Training runs to completion
- Per-epoch metrics are persisted to database
- Experiment lifecycle transitions correctly
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from torch.utils.data import DataLoader, TensorDataset

from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.infrastructure.database import Base
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.types import ExperimentStatus


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
async def async_engine():
    """Create async SQLite in-memory engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def session(async_engine) -> AsyncSession:
    """Create async session for testing."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def experiment_repo(session: AsyncSession) -> ExperimentRepository:
    """Create experiment repository with real database."""
    return ExperimentRepository(session)


@pytest.fixture
def metrics_repo(session: AsyncSession) -> MetricsRepository:
    """Create metrics repository with real database."""
    return MetricsRepository(session)


@pytest.fixture
def experiment_service(
    experiment_repo: ExperimentRepository,
    metrics_repo: MetricsRepository,
) -> ExperimentService:
    """Create experiment service with real repositories."""
    return ExperimentService(experiment_repo, metrics_repo)


@pytest.fixture
def metrics_service(
    metrics_repo: MetricsRepository,
    experiment_repo: ExperimentRepository,
) -> MetricsService:
    """Create metrics service with real repositories."""
    return MetricsService(metrics_repo, experiment_repo)


@pytest.fixture
def synthetic_data_loader() -> MagicMock:
    """Create a mocked DatasetLoader with synthetic rating data.

    Uses small dataset for fast test execution while still exercising
    the full training loop.
    """
    n_samples = 200
    n_users = 50
    n_items = 30

    user_ids = torch.randint(0, n_users, (n_samples,))
    item_ids = torch.randint(0, n_items, (n_samples,))
    ratings = torch.rand(n_samples) * 4 + 1  # Ratings 1-5

    dataset = TensorDataset(user_ids, item_ids, ratings)

    loader = MagicMock()
    loader.load = MagicMock()
    loader.n_users = n_users
    loader.n_items = n_items
    loader.global_mean = 3.0
    loader.get_train_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=True)
    )
    loader.get_val_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=False)
    )

    return loader


@pytest.fixture
def experiment_manager(
    experiment_service: ExperimentService,
    metrics_service: MetricsService,
) -> ExperimentManager:
    """Create ExperimentManager with real services."""
    return ExperimentManager(
        experiment_service=experiment_service,
        metrics_service=metrics_service,
        data_dir=Path("data"),  # Will be mocked
        batch_size=64,
    )


# -----------------------------------------------------------------------------
# Integration Tests: Centralized Training Pipeline
# -----------------------------------------------------------------------------


class TestCentralizedTrainingPipeline:
    """End-to-end tests for centralized training with real database."""

    @pytest.mark.asyncio
    async def test_training_persists_metrics_to_database(
        self,
        experiment_manager: ExperimentManager,
        metrics_repo: MetricsRepository,
        synthetic_data_loader: MagicMock,
    ) -> None:
        """Training run persists per-epoch metrics to database.

        This is the key acceptance criteria for Day 3-4:
        'Records metrics to database'
        """
        config = Configuration(n_factors=8, n_epochs=2, learning_rate=0.01)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=synthetic_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Persistence Test",
                config=config,
                accelerator="cpu",
            )

        # Query database directly to verify persistence
        persisted_metrics = await metrics_repo.get_by_experiment(result.experiment_id)

        # Should have metrics for each epoch
        assert len(persisted_metrics) > 0, "No metrics were persisted to database"

        # Verify metric types
        metric_names = {m.name for m in persisted_metrics}
        assert "loss" in metric_names, "Training loss not persisted"
        assert "rmse" in metric_names, "Validation RMSE not persisted"

        # Verify metrics have round numbers (epochs)
        rounds = {m.round_number for m in persisted_metrics if m.round_number is not None}
        assert 0 in rounds or 1 in rounds, "Epoch metrics not recorded with round numbers"

    @pytest.mark.asyncio
    async def test_experiment_lifecycle_transitions_correctly(
        self,
        experiment_manager: ExperimentManager,
        experiment_repo: ExperimentRepository,
        synthetic_data_loader: MagicMock,
    ) -> None:
        """Experiment transitions PENDING → RUNNING → COMPLETED."""
        config = Configuration(n_factors=8, n_epochs=2)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=synthetic_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Lifecycle Test",
                config=config,
                accelerator="cpu",
            )

        # Verify final state in database
        persisted = await experiment_repo.get_by_id(result.experiment_id)

        assert persisted is not None
        assert persisted.status == ExperimentStatus.COMPLETED
        assert persisted.completed_at is not None
        assert persisted.get_final_rmse() is not None

    @pytest.mark.asyncio
    async def test_experiment_records_final_metrics(
        self,
        experiment_manager: ExperimentManager,
        experiment_repo: ExperimentRepository,
        synthetic_data_loader: MagicMock,
    ) -> None:
        """Completed experiment has final RMSE and MAE recorded."""
        config = Configuration(n_factors=8, n_epochs=2)

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=synthetic_data_loader
        ):
            result = await experiment_manager.run_centralized_experiment(
                name="Final Metrics Test",
                config=config,
                accelerator="cpu",
            )

        # Verify final metrics
        final_rmse = result.get_final_rmse()
        final_mae = result.get_final_mae()

        assert final_rmse is not None, "Final RMSE not recorded"
        assert final_mae is not None, "Final MAE not recorded"
        assert final_rmse > 0, "Invalid RMSE value"
        assert final_mae > 0, "Invalid MAE value"

    @pytest.mark.asyncio
    async def test_training_failure_marks_experiment_failed(
        self,
        experiment_manager: ExperimentManager,
        experiment_repo: ExperimentRepository,
        synthetic_data_loader: MagicMock,
    ) -> None:
        """Training failure correctly marks experiment as FAILED."""
        config = Configuration(n_factors=8, n_epochs=2)

        # Make training fail
        synthetic_data_loader.get_train_loader.side_effect = RuntimeError("Data error")

        with patch.object(
            experiment_manager, "_ensure_data_loaded", return_value=synthetic_data_loader
        ):
            with pytest.raises(RuntimeError, match="Data error"):
                await experiment_manager.run_centralized_experiment(
                    name="Failure Test",
                    config=config,
                    accelerator="cpu",
                )

        # Get all experiments and find the failed one
        all_experiments = await experiment_repo.get_all()
        failed_experiments = [
            exp for exp in all_experiments if exp.status == ExperimentStatus.FAILED
        ]

        assert len(failed_experiments) == 1
        assert failed_experiments[0].name == "Failure Test"
