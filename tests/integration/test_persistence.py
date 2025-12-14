"""Integration tests for persistence layer.

Tests end-to-end database operations including:
- Experiment lifecycle (create, run, complete)
- Metrics recording and retrieval
- Cross-repository operations
"""

import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.core.metrics import ExperimentMetrics, PerformanceMetric
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
    """Create experiment repository."""
    return ExperimentRepository(session)


@pytest.fixture
def metrics_repo(session: AsyncSession) -> MetricsRepository:
    """Create metrics repository."""
    return MetricsRepository(session)


@pytest.fixture
def config() -> Configuration:
    """Create test configuration."""
    return Configuration(n_factors=20, n_epochs=10)


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


class TestExperimentLifecycle:
    """Tests for complete experiment lifecycle."""

    async def test_centralized_experiment_full_lifecycle(
        self,
        experiment_repo: ExperimentRepository,
        config: Configuration,
    ) -> None:
        """Test complete lifecycle of centralized experiment."""
        # 1. Create experiment
        exp = CentralizedExperiment(name="Baseline Test", config=config)
        await experiment_repo.add(exp)

        # Verify created
        retrieved = await experiment_repo.get_by_id(exp.experiment_id)
        assert retrieved is not None
        assert retrieved.status == ExperimentStatus.PENDING

        # 2. Start experiment
        exp.mark_running()
        await experiment_repo.update(exp)

        retrieved = await experiment_repo.get_by_id(exp.experiment_id)
        assert retrieved is not None
        assert retrieved.status == ExperimentStatus.RUNNING

        # 3. Record training metrics
        for epoch in range(1, 6):
            exp.add_epoch_metric(
                PerformanceMetric(
                    name="rmse", value=1.0 - epoch * 0.1, round_number=epoch
                )
            )
        await experiment_repo.update(exp)

        # 4. Complete experiment
        exp.mark_completed(
            ExperimentMetrics(rmse=0.5, mae=0.4, training_time_seconds=60.0)
        )
        await experiment_repo.update(exp)

        # Verify final state
        final = await experiment_repo.get_by_id(exp.experiment_id)
        assert final is not None
        assert final.status == ExperimentStatus.COMPLETED
        assert final.get_final_rmse() == 0.5
        assert len(final.get_training_timeline()) == 5

    async def test_federated_experiment_full_lifecycle(
        self,
        experiment_repo: ExperimentRepository,
        config: Configuration,
    ) -> None:
        """Test complete lifecycle of federated experiment."""
        # 1. Create experiment
        exp = FederatedExperiment(
            name="FedAvg Test", config=config, n_clients=3, n_rounds=5
        )
        await experiment_repo.add(exp)

        # 2. Start and simulate rounds
        exp.mark_running()

        for round_num in range(1, 6):
            # Global metric per round
            exp.add_round_metric(
                PerformanceMetric(
                    name="rmse", value=1.0 - round_num * 0.1, round_number=round_num
                )
            )
            # Client metrics per round
            for client_id in ["client_0", "client_1", "client_2"]:
                exp.add_client_metric(
                    client_id,
                    PerformanceMetric(
                        name="loss",
                        value=0.5 - round_num * 0.05,
                        round_number=round_num,
                        client_id=client_id,
                    ),
                )

        await experiment_repo.update(exp)

        # 3. Complete experiment
        exp.mark_completed(
            ExperimentMetrics(rmse=0.5, mae=0.4, training_time_seconds=120.0)
        )
        await experiment_repo.update(exp)

        # Verify final state
        final = await experiment_repo.get_by_id(exp.experiment_id)
        assert final is not None
        assert isinstance(final, FederatedExperiment)
        assert final.status == ExperimentStatus.COMPLETED
        assert len(final.get_training_timeline()) == 5
        assert len(final.get_client_ids()) == 3
        assert final.n_clients == 3
        assert final.n_rounds == 5


class TestCrossRepositoryOperations:
    """Tests for operations spanning multiple repositories."""

    async def test_metrics_linked_to_experiment(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        config: Configuration,
    ) -> None:
        """Metrics added via MetricsRepository are linked to experiment."""
        # Create experiment
        exp = CentralizedExperiment(name="Metrics Link Test", config=config)
        await experiment_repo.add(exp)

        # Add metrics via metrics repository
        metrics = [
            PerformanceMetric(name="rmse", value=1.0, round_number=1),
            PerformanceMetric(name="rmse", value=0.9, round_number=2),
            PerformanceMetric(name="rmse", value=0.8, round_number=3),
        ]
        await metrics_repo.add_batch(metrics, exp.experiment_id)

        # Retrieve via metrics repository
        retrieved_metrics = await metrics_repo.get_by_experiment(exp.experiment_id)
        assert len(retrieved_metrics) == 3

        # Verify stats
        stats = await metrics_repo.get_metric_stats(exp.experiment_id, "rmse")
        assert stats["min"] == 0.8
        assert stats["max"] == 1.0
        assert stats["count"] == 3

    async def test_delete_experiment_cascades_metrics(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        config: Configuration,
        session: AsyncSession,
    ) -> None:
        """Deleting experiment cascades to delete related metrics."""
        # Create experiment with metrics embedded in entity
        exp = CentralizedExperiment(name="Cascade Test", config=config)
        exp.add_epoch_metric(PerformanceMetric(name="rmse", value=0.9, round_number=1))
        exp.add_epoch_metric(PerformanceMetric(name="loss", value=0.5, round_number=2))
        await experiment_repo.add(exp)

        # Commit to ensure data is persisted
        await session.commit()

        # Verify metrics exist
        metrics_before = await metrics_repo.get_by_experiment(exp.experiment_id)
        assert len(metrics_before) == 2

        # Delete experiment - CASCADE should remove related metrics
        await experiment_repo.delete(exp.experiment_id)
        await session.commit()

        # Verify metrics are gone (CASCADE DELETE)
        remaining = await metrics_repo.get_by_experiment(exp.experiment_id)
        assert len(remaining) == 0


class TestExperimentComparison:
    """Tests for comparing centralized vs federated experiments."""

    async def test_retrieve_experiments_for_comparison(
        self,
        experiment_repo: ExperimentRepository,
        config: Configuration,
    ) -> None:
        """Can retrieve and compare centralized vs federated experiments."""
        # Create both experiment types
        centralized = CentralizedExperiment(name="Baseline", config=config)
        centralized.mark_running()
        centralized.mark_completed(
            ExperimentMetrics(rmse=0.85, mae=0.65, training_time_seconds=60.0)
        )

        federated = FederatedExperiment(
            name="FedAvg", config=config, n_clients=5, n_rounds=10
        )
        federated.mark_running()
        federated.mark_completed(
            ExperimentMetrics(rmse=0.90, mae=0.70, training_time_seconds=120.0)
        )

        await experiment_repo.add(centralized)
        await experiment_repo.add(federated)

        # Retrieve by type for comparison
        centralized_exps = await experiment_repo.get_by_type("centralized")
        federated_exps = await experiment_repo.get_by_type("federated")

        assert len(centralized_exps) == 1
        assert len(federated_exps) == 1

        # Compare metrics
        c = centralized_exps[0]
        f = federated_exps[0]

        assert c.get_final_rmse() is not None
        assert f.get_final_rmse() is not None
        rmse_diff = f.get_final_rmse() - c.get_final_rmse()  # type: ignore
        assert rmse_diff == pytest.approx(0.05, abs=0.001)

    async def test_query_completed_experiments(
        self,
        experiment_repo: ExperimentRepository,
        config: Configuration,
    ) -> None:
        """Can query all completed experiments for dashboard."""
        # Create mix of experiment states
        pending = CentralizedExperiment(name="Pending", config=config)

        running = CentralizedExperiment(name="Running", config=config)
        running.mark_running()

        completed1 = CentralizedExperiment(name="Completed 1", config=config)
        completed1.mark_running()
        completed1.mark_completed(
            ExperimentMetrics(rmse=0.8, mae=0.6, training_time_seconds=50.0)
        )

        completed2 = FederatedExperiment(name="Completed 2", config=config)
        completed2.mark_running()
        completed2.mark_completed(
            ExperimentMetrics(rmse=0.85, mae=0.65, training_time_seconds=100.0)
        )

        for exp in [pending, running, completed1, completed2]:
            await experiment_repo.add(exp)

        # Query completed only
        completed = await experiment_repo.get_by_status(ExperimentStatus.COMPLETED)

        assert len(completed) == 2
        for exp in completed:
            assert exp.status == ExperimentStatus.COMPLETED
            assert exp.get_final_rmse() is not None


class TestDataIntegrity:
    """Tests for data integrity and consistency."""

    async def test_experiment_timestamps_preserved(
        self,
        experiment_repo: ExperimentRepository,
        config: Configuration,
    ) -> None:
        """Experiment timestamps are preserved through persistence."""
        exp = CentralizedExperiment(name="Timestamp Test", config=config)
        original_created = exp.created_at

        await experiment_repo.add(exp)
        retrieved = await experiment_repo.get_by_id(exp.experiment_id)

        assert retrieved is not None
        assert retrieved.created_at == original_created
        assert retrieved.completed_at is None

        # Complete and verify completed_at
        exp.mark_running()
        exp.mark_completed(
            ExperimentMetrics(rmse=0.8, mae=0.6, training_time_seconds=30.0)
        )
        await experiment_repo.update(exp)

        final = await experiment_repo.get_by_id(exp.experiment_id)
        assert final is not None
        assert final.completed_at is not None

    async def test_metric_values_preserved_with_precision(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        config: Configuration,
    ) -> None:
        """Metric values maintain precision through persistence."""
        exp = CentralizedExperiment(name="Precision Test", config=config)
        await experiment_repo.add(exp)

        precise_value = 0.123456789
        await metrics_repo.add(
            PerformanceMetric(name="rmse", value=precise_value, round_number=1),
            exp.experiment_id,
        )

        retrieved = await metrics_repo.get_by_experiment(exp.experiment_id)
        assert len(retrieved) == 1
        assert retrieved[0].value == pytest.approx(precise_value, rel=1e-9)
