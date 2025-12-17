"""Unit tests for MetricsService.

Tests business logic layer for metrics operations.
Uses SQLite in-memory database with real repositories.
"""

import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.core.metrics import PerformanceMetric
from app.infrastructure.database import Base
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.exceptions import ConfigurationError, EntityNotFoundError


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
def metrics_service(
    metrics_repo: MetricsRepository, experiment_repo: ExperimentRepository
) -> MetricsService:
    """Create metrics service with test repositories."""
    return MetricsService(metrics_repo, experiment_repo)


@pytest.fixture
def default_config() -> Configuration:
    """Create default configuration."""
    return Configuration(n_factors=20, n_epochs=10)


@pytest.fixture
async def centralized_experiment(
    experiment_repo: ExperimentRepository, default_config: Configuration
) -> CentralizedExperiment:
    """Create and persist centralized experiment."""
    experiment = CentralizedExperiment(name="Test Baseline", config=default_config)
    await experiment_repo.add(experiment)
    return experiment


@pytest.fixture
async def federated_experiment(
    experiment_repo: ExperimentRepository, default_config: Configuration
) -> FederatedExperiment:
    """Create and persist federated experiment."""
    experiment = FederatedExperiment(
        name="Test Federated", config=default_config, n_clients=5, n_rounds=10
    )
    await experiment_repo.add(experiment)
    return experiment


# -----------------------------------------------------------------------------
# Test Add Metric
# -----------------------------------------------------------------------------


class TestAddMetric:
    """Tests for MetricsService.add_metric()."""

    @pytest.mark.asyncio
    async def test_add_metric_success(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can add metric to existing experiment."""
        metric = await metrics_service.add_metric(
            experiment_id=centralized_experiment.experiment_id,
            name="rmse",
            value=0.95,
            round_number=1,
        )

        assert metric.name == "rmse"
        assert metric.value == 0.95
        assert metric.experiment_id == centralized_experiment.experiment_id
        assert metric.round_number == 1

    @pytest.mark.asyncio
    async def test_add_metric_with_context(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can add metric with context."""
        metric = await metrics_service.add_metric(
            experiment_id=centralized_experiment.experiment_id,
            name="loss",
            value=0.5,
            context="global",
        )

        assert metric.context == "global"

    @pytest.mark.asyncio
    async def test_add_metric_with_client_id(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Can add metric with client ID."""
        metric = await metrics_service.add_metric(
            experiment_id=federated_experiment.experiment_id,
            name="loss",
            value=0.5,
            client_id="client_1",
            round_number=1,
        )

        assert metric.client_id == "client_1"

    @pytest.mark.asyncio
    async def test_add_metric_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Adding metric to nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.add_metric(
                experiment_id="nonexistent-id", name="rmse", value=0.95
            )

    @pytest.mark.asyncio
    async def test_add_metric_empty_name_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Adding metric with empty name raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="cannot be empty"):
            await metrics_service.add_metric(
                experiment_id=centralized_experiment.experiment_id, name="", value=0.95
            )


# -----------------------------------------------------------------------------
# Test Add Metrics Batch
# -----------------------------------------------------------------------------


class TestAddMetricsBatch:
    """Tests for MetricsService.add_metrics_batch()."""

    @pytest.mark.asyncio
    async def test_add_batch_success(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can add multiple metrics in batch."""
        metrics = [
            PerformanceMetric(
                name="rmse",
                value=1.0,
                experiment_id=centralized_experiment.experiment_id,
                round_number=1,
            ),
            PerformanceMetric(
                name="rmse",
                value=0.9,
                experiment_id=centralized_experiment.experiment_id,
                round_number=2,
            ),
            PerformanceMetric(
                name="mae",
                value=0.8,
                experiment_id=centralized_experiment.experiment_id,
                round_number=1,
            ),
        ]

        result = await metrics_service.add_metrics_batch(
            centralized_experiment.experiment_id, metrics
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_add_batch_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Adding batch to nonexistent experiment raises EntityNotFoundError."""
        metrics = [
            PerformanceMetric(name="rmse", value=1.0, experiment_id="nonexistent-id")
        ]

        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.add_metrics_batch("nonexistent-id", metrics)

    @pytest.mark.asyncio
    async def test_add_batch_empty_list_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Adding empty metrics list raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="cannot be empty"):
            await metrics_service.add_metrics_batch(
                centralized_experiment.experiment_id, []
            )

    @pytest.mark.asyncio
    async def test_add_batch_mismatched_experiment_id_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Adding batch with mismatched experiment_id raises ConfigurationError."""
        metrics = [
            PerformanceMetric(
                name="rmse",
                value=1.0,
                experiment_id="different-experiment-id",
                round_number=1,
            )
        ]

        with pytest.raises(ConfigurationError, match="does not match"):
            await metrics_service.add_metrics_batch(
                centralized_experiment.experiment_id, metrics
            )


# -----------------------------------------------------------------------------
# Test Get Metrics
# -----------------------------------------------------------------------------


class TestGetExperimentMetrics:
    """Tests for MetricsService.get_experiment_metrics()."""

    @pytest.mark.asyncio
    async def test_get_experiment_metrics(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can retrieve all metrics for an experiment."""
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.8, round_number=1
        )

        metrics = await metrics_service.get_experiment_metrics(
            centralized_experiment.experiment_id
        )

        assert len(metrics) == 3

    @pytest.mark.asyncio
    async def test_get_experiment_metrics_nonexistent_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting metrics for nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_experiment_metrics("nonexistent-id")


class TestGetMetricsByName:
    """Tests for MetricsService.get_metrics_by_name()."""

    @pytest.mark.asyncio
    async def test_filters_by_metric_name(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Filters metrics by name correctly."""
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.8, round_number=1
        )

        rmse_metrics = await metrics_service.get_metrics_by_name(
            centralized_experiment.experiment_id, "rmse"
        )
        mae_metrics = await metrics_service.get_metrics_by_name(
            centralized_experiment.experiment_id, "mae"
        )

        assert len(rmse_metrics) == 2
        assert len(mae_metrics) == 1

    @pytest.mark.asyncio
    async def test_get_metrics_by_name_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting metrics by name for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_metrics_by_name("nonexistent-id", "rmse")


class TestGetClientMetrics:
    """Tests for MetricsService.get_client_metrics()."""

    @pytest.mark.asyncio
    async def test_get_client_metrics(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Can retrieve metrics for specific client."""
        await metrics_service.add_metric(
            federated_experiment.experiment_id,
            "loss",
            0.5,
            client_id="client_1",
            round_number=1,
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id,
            "loss",
            0.6,
            client_id="client_2",
            round_number=1,
        )

        client1_metrics = await metrics_service.get_client_metrics(
            federated_experiment.experiment_id, "client_1"
        )

        assert len(client1_metrics) == 1
        assert client1_metrics[0].client_id == "client_1"
        assert client1_metrics[0].value == 0.5

    @pytest.mark.asyncio
    async def test_get_client_metrics_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting client metrics for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_client_metrics("nonexistent-id", "client_1")


class TestGetRoundMetrics:
    """Tests for MetricsService.get_round_metrics()."""

    @pytest.mark.asyncio
    async def test_get_round_metrics(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Can retrieve metrics for specific round."""
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "mae", 0.8, round_number=1
        )

        round1_metrics = await metrics_service.get_round_metrics(
            federated_experiment.experiment_id, 1
        )

        assert len(round1_metrics) == 2
        assert all(m.round_number == 1 for m in round1_metrics)

    @pytest.mark.asyncio
    async def test_get_round_metrics_invalid_round_raises_error(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Getting metrics with negative round number raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="must be non-negative"):
            await metrics_service.get_round_metrics(
                federated_experiment.experiment_id, -1
            )

    @pytest.mark.asyncio
    async def test_get_round_metrics_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting round metrics for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_round_metrics("nonexistent-id", 1)


# -----------------------------------------------------------------------------
# Test Statistics
# -----------------------------------------------------------------------------


class TestGetMetricStatistics:
    """Tests for MetricsService.get_metric_statistics()."""

    @pytest.mark.asyncio
    async def test_get_statistics(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can calculate aggregate statistics for metrics."""
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.8, round_number=2
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.6, round_number=3
        )

        stats = await metrics_service.get_metric_statistics(
            centralized_experiment.experiment_id, "rmse"
        )

        assert stats["min"] == 0.6
        assert stats["max"] == 1.0
        assert stats["count"] == 3
        assert abs(stats["avg"] - 0.8) < 0.01

    @pytest.mark.asyncio
    async def test_get_statistics_no_metrics_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Getting statistics with no metrics raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError, match="No metrics found"):
            await metrics_service.get_metric_statistics(
                centralized_experiment.experiment_id, "nonexistent"
            )

    @pytest.mark.asyncio
    async def test_get_statistics_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting statistics for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_metric_statistics("nonexistent-id", "rmse")


# -----------------------------------------------------------------------------
# Test Calculate Final Metrics
# -----------------------------------------------------------------------------


class TestCalculateFinalMetrics:
    """Tests for MetricsService.calculate_final_metrics()."""

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_success(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can calculate final metrics from training metrics."""
        # Add metrics for multiple rounds
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.85, round_number=3
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.8, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.7, round_number=2
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.65, round_number=3
        )

        final_metrics = await metrics_service.calculate_final_metrics(
            centralized_experiment.experiment_id
        )

        assert final_metrics["rmse"] == 0.85
        assert final_metrics["mae"] == 0.65

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_uses_last_value(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Uses the last recorded value for each metric."""
        # Add metrics in non-sequential order
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.85, round_number=3
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "mae", 0.75, round_number=2
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "mae", 0.8, round_number=1
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "mae", 0.7, round_number=3
        )

        final_metrics = await metrics_service.calculate_final_metrics(
            federated_experiment.experiment_id
        )

        # Should use the last round (round 3)
        assert final_metrics["rmse"] == 0.85
        assert final_metrics["mae"] == 0.7

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Calculating metrics for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.calculate_final_metrics("nonexistent-id")

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_no_metrics_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Calculating metrics with no data raises error."""
        with pytest.raises(EntityNotFoundError, match="No metrics found"):
            await metrics_service.calculate_final_metrics(
                centralized_experiment.experiment_id
            )

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_missing_rmse_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Calculating metrics without RMSE raises ConfigurationError."""
        # Only add MAE metrics
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.8, round_number=1
        )

        with pytest.raises(ConfigurationError, match="No RMSE metrics found"):
            await metrics_service.calculate_final_metrics(
                centralized_experiment.experiment_id
            )

    @pytest.mark.asyncio
    async def test_calculate_final_metrics_missing_mae_raises_error(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Calculating metrics without MAE raises ConfigurationError."""
        # Only add RMSE metrics
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 0.9, round_number=1
        )

        with pytest.raises(ConfigurationError, match="No MAE metrics found"):
            await metrics_service.calculate_final_metrics(
                centralized_experiment.experiment_id
            )


# -----------------------------------------------------------------------------
# Test Delete Operations
# -----------------------------------------------------------------------------


class TestDeleteExperimentMetrics:
    """Tests for MetricsService.delete_experiment_metrics()."""

    @pytest.mark.asyncio
    async def test_delete_experiment_metrics(
        self,
        metrics_service: MetricsService,
        centralized_experiment: CentralizedExperiment,
    ):
        """Can delete all metrics for an experiment."""
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            centralized_experiment.experiment_id, "mae", 0.8, round_number=1
        )

        await metrics_service.delete_experiment_metrics(
            centralized_experiment.experiment_id
        )

        metrics = await metrics_service.get_experiment_metrics(
            centralized_experiment.experiment_id
        )
        assert len(metrics) == 0

    @pytest.mark.asyncio
    async def test_delete_metrics_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Deleting metrics for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.delete_experiment_metrics("nonexistent-id")


# -----------------------------------------------------------------------------
# Test Analysis Methods
# -----------------------------------------------------------------------------


class TestGetConvergenceAnalysis:
    """Tests for MetricsService.get_convergence_analysis()."""

    @pytest.mark.asyncio
    async def test_get_convergence_analysis(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Can get convergence analysis by round."""
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.9, round_number=2
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.8, round_number=3
        )

        convergence = await metrics_service.get_convergence_analysis(
            federated_experiment.experiment_id, "rmse"
        )

        assert len(convergence) == 3
        assert convergence[0]["round_number"] == 1
        assert convergence[0]["value"] == 1.0
        assert convergence[1]["round_number"] == 2
        assert convergence[1]["value"] == 0.9

    @pytest.mark.asyncio
    async def test_convergence_analysis_sorted_by_round(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Convergence analysis results are sorted by round number."""
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.8, round_number=3
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 1.0, round_number=1
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id, "rmse", 0.9, round_number=2
        )

        convergence = await metrics_service.get_convergence_analysis(
            federated_experiment.experiment_id, "rmse"
        )

        assert convergence[0]["round_number"] == 1
        assert convergence[1]["round_number"] == 2
        assert convergence[2]["round_number"] == 3

    @pytest.mark.asyncio
    async def test_convergence_analysis_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting convergence analysis for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_convergence_analysis("nonexistent-id", "rmse")


class TestGetClientPerformanceComparison:
    """Tests for MetricsService.get_client_performance_comparison()."""

    @pytest.mark.asyncio
    async def test_get_client_performance_comparison(
        self,
        metrics_service: MetricsService,
        federated_experiment: FederatedExperiment,
    ):
        """Can compare average performance across clients."""
        await metrics_service.add_metric(
            federated_experiment.experiment_id,
            "rmse",
            1.0,
            client_id="client_1",
            round_number=1,
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id,
            "rmse",
            0.8,
            client_id="client_1",
            round_number=2,
        )
        await metrics_service.add_metric(
            federated_experiment.experiment_id,
            "rmse",
            0.9,
            client_id="client_2",
            round_number=1,
        )

        comparison = await metrics_service.get_client_performance_comparison(
            federated_experiment.experiment_id, "rmse"
        )

        assert "client_1" in comparison
        assert "client_2" in comparison
        assert abs(comparison["client_1"] - 0.9) < 0.01
        assert comparison["client_2"] == 0.9

    @pytest.mark.asyncio
    async def test_client_comparison_nonexistent_experiment_raises_error(
        self, metrics_service: MetricsService
    ):
        """Getting client comparison for nonexistent experiment raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await metrics_service.get_client_performance_comparison(
                "nonexistent-id", "rmse"
            )
