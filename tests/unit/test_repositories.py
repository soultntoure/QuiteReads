"""Unit tests for repository implementations.

Uses SQLite in-memory database for fast, isolated testing.
Tests cover CRUD operations and domain entity conversion.
"""

import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.core.metrics import ExperimentMetrics, PerformanceMetric
from app.infrastructure.database import Base
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.exceptions import EntityNotFoundError, RepositoryError
from app.utils.types import AggregationStrategy, ExperimentStatus


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
    """Create experiment repository with test session."""
    return ExperimentRepository(session)


@pytest.fixture
def metrics_repo(session: AsyncSession) -> MetricsRepository:
    """Create metrics repository with test session."""
    return MetricsRepository(session)


@pytest.fixture
def default_config() -> Configuration:
    """Create default configuration."""
    return Configuration(n_factors=20, n_epochs=10)


@pytest.fixture
def centralized_experiment(default_config: Configuration) -> CentralizedExperiment:
    """Create centralized experiment."""
    return CentralizedExperiment(name="Test Baseline", config=default_config)


@pytest.fixture
def federated_experiment(default_config: Configuration) -> FederatedExperiment:
    """Create federated experiment."""
    return FederatedExperiment(
        name="Test Federated",
        config=default_config,
        n_clients=5,
        n_rounds=10,
    )


@pytest.fixture
def sample_metrics() -> list[PerformanceMetric]:
    """Create sample performance metrics."""
    return [
        PerformanceMetric(name="rmse", value=1.0, round_number=1),
        PerformanceMetric(name="rmse", value=0.9, round_number=2),
        PerformanceMetric(name="rmse", value=0.8, round_number=3),
        PerformanceMetric(name="loss", value=0.5, round_number=1),
        PerformanceMetric(name="loss", value=0.4, round_number=2),
    ]


# -----------------------------------------------------------------------------
# ExperimentRepository Tests
# -----------------------------------------------------------------------------


class TestExperimentRepositoryAdd:
    """Tests for ExperimentRepository.add()."""

    async def test_add_centralized_experiment(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can add centralized experiment."""
        result = await experiment_repo.add(centralized_experiment)
        assert result.experiment_id == centralized_experiment.experiment_id
        assert result.name == "Test Baseline"

    async def test_add_federated_experiment(
        self,
        experiment_repo: ExperimentRepository,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """Can add federated experiment."""
        result = await experiment_repo.add(federated_experiment)
        assert result.experiment_id == federated_experiment.experiment_id
        assert result.name == "Test Federated"

    async def test_add_experiment_with_metrics(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can add experiment with training metrics."""
        centralized_experiment.add_epoch_metric(
            PerformanceMetric(name="rmse", value=0.95, round_number=1)
        )
        centralized_experiment.add_epoch_metric(
            PerformanceMetric(name="rmse", value=0.85, round_number=2)
        )

        result = await experiment_repo.add(centralized_experiment)
        assert len(result.epoch_metrics) == 2


class TestExperimentRepositoryGetById:
    """Tests for ExperimentRepository.get_by_id()."""

    async def test_get_existing_centralized(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can retrieve centralized experiment by ID."""
        await experiment_repo.add(centralized_experiment)
        result = await experiment_repo.get_by_id(centralized_experiment.experiment_id)

        assert result is not None
        assert result.experiment_id == centralized_experiment.experiment_id
        assert result.experiment_type == "centralized"
        assert result.name == "Test Baseline"

    async def test_get_existing_federated(
        self,
        experiment_repo: ExperimentRepository,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """Can retrieve federated experiment by ID."""
        await experiment_repo.add(federated_experiment)
        result = await experiment_repo.get_by_id(federated_experiment.experiment_id)

        assert result is not None
        assert result.experiment_type == "federated"
        assert isinstance(result, FederatedExperiment)
        assert result.n_clients == 5
        assert result.n_rounds == 10

    async def test_get_nonexistent_returns_none(
        self, experiment_repo: ExperimentRepository
    ) -> None:
        """Returns None for nonexistent experiment."""
        result = await experiment_repo.get_by_id("nonexistent-id")
        assert result is None

    async def test_get_preserves_config(
        self,
        experiment_repo: ExperimentRepository,
        default_config: Configuration,
    ) -> None:
        """Retrieved experiment preserves configuration."""
        exp = CentralizedExperiment(name="Config Test", config=default_config)
        await experiment_repo.add(exp)
        result = await experiment_repo.get_by_id(exp.experiment_id)

        assert result is not None
        assert result.config.n_factors == 20
        assert result.config.n_epochs == 10
        assert result.config.learning_rate == 0.005

    async def test_get_preserves_metrics(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Retrieved experiment preserves training metrics."""
        centralized_experiment.add_epoch_metric(
            PerformanceMetric(name="rmse", value=0.95, round_number=1)
        )
        await experiment_repo.add(centralized_experiment)

        result = await experiment_repo.get_by_id(centralized_experiment.experiment_id)

        assert result is not None
        assert len(result.get_training_timeline()) == 1
        assert result.get_training_timeline()[0].value == 0.95


class TestExperimentRepositoryGetAll:
    """Tests for ExperimentRepository.get_all()."""

    async def test_get_all_empty(self, experiment_repo: ExperimentRepository) -> None:
        """Returns empty list when no experiments."""
        result = await experiment_repo.get_all()
        assert result == []

    async def test_get_all_multiple(
        self,
        experiment_repo: ExperimentRepository,
        default_config: Configuration,
    ) -> None:
        """Returns all experiments."""
        exp1 = CentralizedExperiment(name="Exp 1", config=default_config)
        exp2 = FederatedExperiment(name="Exp 2", config=default_config)

        await experiment_repo.add(exp1)
        await experiment_repo.add(exp2)

        result = await experiment_repo.get_all()
        assert len(result) == 2


class TestExperimentRepositoryGetByStatus:
    """Tests for ExperimentRepository.get_by_status()."""

    async def test_get_by_status_filters_correctly(
        self,
        experiment_repo: ExperimentRepository,
        default_config: Configuration,
    ) -> None:
        """Filters experiments by status."""
        exp1 = CentralizedExperiment(name="Pending", config=default_config)
        exp2 = CentralizedExperiment(name="Running", config=default_config)
        exp2.mark_running()

        await experiment_repo.add(exp1)
        await experiment_repo.add(exp2)

        pending = await experiment_repo.get_by_status(ExperimentStatus.PENDING)
        running = await experiment_repo.get_by_status(ExperimentStatus.RUNNING)

        assert len(pending) == 1
        assert pending[0].name == "Pending"
        assert len(running) == 1
        assert running[0].name == "Running"


class TestExperimentRepositoryGetByType:
    """Tests for ExperimentRepository.get_by_type()."""

    async def test_get_by_type_filters_correctly(
        self,
        experiment_repo: ExperimentRepository,
        default_config: Configuration,
    ) -> None:
        """Filters experiments by type."""
        exp1 = CentralizedExperiment(name="Centralized", config=default_config)
        exp2 = FederatedExperiment(name="Federated", config=default_config)

        await experiment_repo.add(exp1)
        await experiment_repo.add(exp2)

        centralized = await experiment_repo.get_by_type("centralized")
        federated = await experiment_repo.get_by_type("federated")

        assert len(centralized) == 1
        assert centralized[0].name == "Centralized"
        assert len(federated) == 1
        assert federated[0].name == "Federated"


class TestExperimentRepositoryUpdate:
    """Tests for ExperimentRepository.update()."""

    async def test_update_status(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can update experiment status."""
        await experiment_repo.add(centralized_experiment)

        centralized_experiment.mark_running()
        await experiment_repo.update(centralized_experiment)

        result = await experiment_repo.get_by_id(centralized_experiment.experiment_id)
        assert result is not None
        assert result.status == ExperimentStatus.RUNNING

    async def test_update_with_final_metrics(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can update experiment with final metrics."""
        await experiment_repo.add(centralized_experiment)

        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(
            ExperimentMetrics(rmse=0.85, mae=0.65, training_time_seconds=120.0)
        )
        await experiment_repo.update(centralized_experiment)

        result = await experiment_repo.get_by_id(centralized_experiment.experiment_id)
        assert result is not None
        assert result.get_final_rmse() == 0.85
        assert result.get_final_mae() == 0.65

    async def test_update_nonexistent_raises_error(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Updating nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            await experiment_repo.update(centralized_experiment)


class TestExperimentRepositoryDelete:
    """Tests for ExperimentRepository.delete()."""

    async def test_delete_existing(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can delete existing experiment."""
        await experiment_repo.add(centralized_experiment)
        result = await experiment_repo.delete(centralized_experiment.experiment_id)

        assert result is True
        assert await experiment_repo.get_by_id(centralized_experiment.experiment_id) is None

    async def test_delete_nonexistent_returns_false(
        self, experiment_repo: ExperimentRepository
    ) -> None:
        """Deleting nonexistent experiment returns False."""
        result = await experiment_repo.delete("nonexistent-id")
        assert result is False


class TestExperimentRepositoryExists:
    """Tests for ExperimentRepository.exists()."""

    async def test_exists_true(
        self,
        experiment_repo: ExperimentRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Returns True for existing experiment."""
        await experiment_repo.add(centralized_experiment)
        result = await experiment_repo.exists(centralized_experiment.experiment_id)
        assert result is True

    async def test_exists_false(self, experiment_repo: ExperimentRepository) -> None:
        """Returns False for nonexistent experiment."""
        result = await experiment_repo.exists("nonexistent-id")
        assert result is False


class TestExperimentRepositoryFederatedSpecific:
    """Tests for federated experiment-specific functionality."""

    async def test_preserves_client_metrics(
        self,
        experiment_repo: ExperimentRepository,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """Preserves client metrics for federated experiments."""
        federated_experiment.add_client_metric(
            "client_1", PerformanceMetric(name="loss", value=0.5, round_number=1)
        )
        federated_experiment.add_client_metric(
            "client_2", PerformanceMetric(name="loss", value=0.6, round_number=1)
        )

        await experiment_repo.add(federated_experiment)
        result = await experiment_repo.get_by_id(federated_experiment.experiment_id)

        assert result is not None
        assert isinstance(result, FederatedExperiment)
        assert len(result.get_client_ids()) == 2
        assert "client_1" in result.get_client_ids()

    async def test_preserves_aggregation_strategy(
        self,
        experiment_repo: ExperimentRepository,
        default_config: Configuration,
    ) -> None:
        """Preserves aggregation strategy."""
        exp = FederatedExperiment(
            name="FedAvg Test",
            config=default_config,
            aggregation_strategy=AggregationStrategy.FEDAVG,
        )

        await experiment_repo.add(exp)
        result = await experiment_repo.get_by_id(exp.experiment_id)

        assert result is not None
        assert isinstance(result, FederatedExperiment)
        assert result.aggregation_strategy == AggregationStrategy.FEDAVG


# -----------------------------------------------------------------------------
# MetricsRepository Tests
# -----------------------------------------------------------------------------


class TestMetricsRepositoryAdd:
    """Tests for MetricsRepository.add()."""

    async def test_add_single_metric(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can add single metric."""
        await experiment_repo.add(centralized_experiment)

        metric = PerformanceMetric(name="rmse", value=0.95, round_number=1)
        result = await metrics_repo.add(metric, centralized_experiment.experiment_id)

        assert result.name == "rmse"
        assert result.value == 0.95


class TestMetricsRepositoryAddBatch:
    """Tests for MetricsRepository.add_batch()."""

    async def test_add_batch(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
        sample_metrics: list[PerformanceMetric],
    ) -> None:
        """Can add batch of metrics."""
        await experiment_repo.add(centralized_experiment)

        result = await metrics_repo.add_batch(
            sample_metrics, centralized_experiment.experiment_id
        )

        assert len(result) == 5


class TestMetricsRepositoryGetByExperiment:
    """Tests for MetricsRepository.get_by_experiment()."""

    async def test_get_by_experiment(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
        sample_metrics: list[PerformanceMetric],
    ) -> None:
        """Can retrieve metrics by experiment."""
        await experiment_repo.add(centralized_experiment)
        await metrics_repo.add_batch(sample_metrics, centralized_experiment.experiment_id)

        result = await metrics_repo.get_by_experiment(
            centralized_experiment.experiment_id
        )

        assert len(result) == 5


class TestMetricsRepositoryGetByExperimentAndName:
    """Tests for MetricsRepository.get_by_experiment_and_name()."""

    async def test_filters_by_name(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
        sample_metrics: list[PerformanceMetric],
    ) -> None:
        """Filters metrics by name."""
        await experiment_repo.add(centralized_experiment)
        await metrics_repo.add_batch(sample_metrics, centralized_experiment.experiment_id)

        rmse_metrics = await metrics_repo.get_by_experiment_and_name(
            centralized_experiment.experiment_id, "rmse"
        )
        loss_metrics = await metrics_repo.get_by_experiment_and_name(
            centralized_experiment.experiment_id, "loss"
        )

        assert len(rmse_metrics) == 3
        assert len(loss_metrics) == 2


class TestMetricsRepositoryGetClientMetrics:
    """Tests for MetricsRepository.get_client_metrics()."""

    async def test_get_client_metrics(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """Can retrieve client-specific metrics."""
        await experiment_repo.add(federated_experiment)

        await metrics_repo.add(
            PerformanceMetric(name="loss", value=0.5, client_id="client_1"),
            federated_experiment.experiment_id,
        )
        await metrics_repo.add(
            PerformanceMetric(name="loss", value=0.6, client_id="client_2"),
            federated_experiment.experiment_id,
        )

        client1_metrics = await metrics_repo.get_client_metrics(
            federated_experiment.experiment_id, "client_1"
        )

        assert len(client1_metrics) == 1
        assert client1_metrics[0].value == 0.5


class TestMetricsRepositoryGetRoundMetrics:
    """Tests for MetricsRepository.get_round_metrics()."""

    async def test_get_round_metrics(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """Can retrieve round-specific metrics."""
        await experiment_repo.add(federated_experiment)

        await metrics_repo.add(
            PerformanceMetric(name="rmse", value=0.9, round_number=1),
            federated_experiment.experiment_id,
        )
        await metrics_repo.add(
            PerformanceMetric(name="rmse", value=0.8, round_number=2),
            federated_experiment.experiment_id,
        )

        round1_metrics = await metrics_repo.get_round_metrics(
            federated_experiment.experiment_id, 1
        )

        assert len(round1_metrics) == 1
        assert round1_metrics[0].value == 0.9


class TestMetricsRepositoryGetStats:
    """Tests for MetricsRepository.get_metric_stats()."""

    async def test_get_metric_stats(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
    ) -> None:
        """Can get aggregate statistics for metrics."""
        await experiment_repo.add(centralized_experiment)

        metrics = [
            PerformanceMetric(name="rmse", value=1.0, round_number=1),
            PerformanceMetric(name="rmse", value=0.8, round_number=2),
            PerformanceMetric(name="rmse", value=0.6, round_number=3),
        ]
        await metrics_repo.add_batch(metrics, centralized_experiment.experiment_id)

        stats = await metrics_repo.get_metric_stats(
            centralized_experiment.experiment_id, "rmse"
        )

        assert stats["min"] == 0.6
        assert stats["max"] == 1.0
        assert stats["count"] == 3
        assert abs(stats["avg"] - 0.8) < 0.01


class TestMetricsRepositoryDelete:
    """Tests for MetricsRepository.delete()."""

    async def test_delete_by_experiment(
        self,
        experiment_repo: ExperimentRepository,
        metrics_repo: MetricsRepository,
        centralized_experiment: CentralizedExperiment,
        sample_metrics: list[PerformanceMetric],
    ) -> None:
        """Can delete all metrics for an experiment."""
        await experiment_repo.add(centralized_experiment)
        await metrics_repo.add_batch(sample_metrics, centralized_experiment.experiment_id)

        deleted_count = await metrics_repo.delete_by_experiment(
            centralized_experiment.experiment_id
        )

        assert deleted_count == 5

        remaining = await metrics_repo.get_by_experiment(
            centralized_experiment.experiment_id
        )
        assert len(remaining) == 0


class TestMetricsRepositoryUpdate:
    """Tests for MetricsRepository.update()."""

    async def test_update_raises_not_implemented(
        self, metrics_repo: MetricsRepository
    ) -> None:
        """Update raises NotImplementedError (metrics are immutable)."""
        metric = PerformanceMetric(name="rmse", value=0.9)
        with pytest.raises(NotImplementedError):
            await metrics_repo.update(metric)
