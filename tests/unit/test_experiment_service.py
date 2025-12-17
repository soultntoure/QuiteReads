"""Unit tests for ExperimentService.

Tests business logic layer for experiment operations.
Uses SQLite in-memory database with real repositories.
"""

import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.services.experiment_service import ExperimentService
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.infrastructure.database import Base
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.exceptions import ConfigurationError, EntityNotFoundError
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
def experiment_service(
    experiment_repo: ExperimentRepository, metrics_repo: MetricsRepository
) -> ExperimentService:
    """Create experiment service with test repositories."""
    return ExperimentService(experiment_repo, metrics_repo)


@pytest.fixture
def default_config() -> Configuration:
    """Create default configuration."""
    return Configuration(n_factors=20, n_epochs=10)


# -----------------------------------------------------------------------------
# Test Create Centralized Experiment
# -----------------------------------------------------------------------------


class TestCreateCentralizedExperiment:
    """Tests for ExperimentService.create_centralized_experiment()."""

    @pytest.mark.asyncio
    async def test_create_centralized_experiment_success(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can create centralized experiment successfully."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test Baseline", config=default_config
        )

        assert experiment.name == "Test Baseline"
        assert experiment.experiment_type == "centralized"
        assert experiment.status == ExperimentStatus.PENDING
        assert experiment.config.n_factors == 20
        assert experiment.config.n_epochs == 10

    @pytest.mark.asyncio
    async def test_created_experiment_persisted(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Created experiment is persisted to repository."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test Baseline", config=default_config
        )

        retrieved = await experiment_service.get_experiment_by_id(
            experiment.experiment_id
        )
        assert retrieved.name == "Test Baseline"
        assert retrieved.experiment_id == experiment.experiment_id


# -----------------------------------------------------------------------------
# Test Create Federated Experiment
# -----------------------------------------------------------------------------


class TestCreateFederatedExperiment:
    """Tests for ExperimentService.create_federated_experiment()."""

    @pytest.mark.asyncio
    async def test_create_federated_experiment_success(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can create federated experiment successfully."""
        experiment = await experiment_service.create_federated_experiment(
            name="Test Federated",
            config=default_config,
            n_clients=5,
            n_rounds=10,
        )

        assert experiment.name == "Test Federated"
        assert experiment.experiment_type == "federated"
        assert experiment.status == ExperimentStatus.PENDING
        assert experiment.n_clients == 5
        assert experiment.n_rounds == 10
        assert experiment.aggregation_strategy == AggregationStrategy.FEDAVG

    @pytest.mark.asyncio
    async def test_create_with_custom_aggregation(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can create federated experiment with custom aggregation strategy."""
        experiment = await experiment_service.create_federated_experiment(
            name="Test FedAvg",
            config=default_config,
            n_clients=5,
            n_rounds=10,
            aggregation_strategy=AggregationStrategy.FEDAVG,
        )

        assert experiment.aggregation_strategy == AggregationStrategy.FEDAVG

    @pytest.mark.asyncio
    async def test_create_with_invalid_n_clients_raises_error(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Creating federated experiment with invalid n_clients raises error."""
        with pytest.raises(ConfigurationError, match="n_clients must be between"):
            await experiment_service.create_federated_experiment(
                name="Invalid", config=default_config, n_clients=1, n_rounds=10
            )

        with pytest.raises(ConfigurationError, match="n_clients must be between"):
            await experiment_service.create_federated_experiment(
                name="Invalid", config=default_config, n_clients=101, n_rounds=10
            )

    @pytest.mark.asyncio
    async def test_create_with_invalid_n_rounds_raises_error(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Creating federated experiment with invalid n_rounds raises error."""
        with pytest.raises(ConfigurationError, match="n_rounds must be between"):
            await experiment_service.create_federated_experiment(
                name="Invalid", config=default_config, n_clients=5, n_rounds=0
            )

        with pytest.raises(ConfigurationError, match="n_rounds must be between"):
            await experiment_service.create_federated_experiment(
                name="Invalid", config=default_config, n_clients=5, n_rounds=501
            )


# -----------------------------------------------------------------------------
# Test Get Experiment Operations
# -----------------------------------------------------------------------------


class TestGetExperiment:
    """Tests for ExperimentService.get_experiment_by_id()."""

    @pytest.mark.asyncio
    async def test_get_existing_experiment(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can retrieve existing experiment by ID."""
        created = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        retrieved = await experiment_service.get_experiment_by_id(created.experiment_id)
        assert retrieved.experiment_id == created.experiment_id
        assert retrieved.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_experiment_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Getting nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            await experiment_service.get_experiment_by_id("nonexistent-id")


class TestGetAllExperiments:
    """Tests for ExperimentService.get_all_experiments()."""

    @pytest.mark.asyncio
    async def test_get_all_empty(self, experiment_service: ExperimentService):
        """Returns empty list when no experiments exist."""
        result = await experiment_service.get_all_experiments()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_multiple_experiments(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Returns all experiments."""
        await experiment_service.create_centralized_experiment(
            name="Exp 1", config=default_config
        )
        await experiment_service.create_federated_experiment(
            name="Exp 2", config=default_config, n_clients=5, n_rounds=10
        )

        result = await experiment_service.get_all_experiments()
        assert len(result) == 2


class TestGetExperimentsByStatus:
    """Tests for ExperimentService.get_experiments_by_status()."""

    @pytest.mark.asyncio
    async def test_filters_by_status(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Filters experiments by status correctly."""
        exp1 = await experiment_service.create_centralized_experiment(
            name="Pending", config=default_config
        )
        exp2 = await experiment_service.create_centralized_experiment(
            name="Running", config=default_config
        )
        await experiment_service.start_experiment(exp2.experiment_id)

        pending = await experiment_service.get_experiments_by_status(
            ExperimentStatus.PENDING
        )
        running = await experiment_service.get_experiments_by_status(
            ExperimentStatus.RUNNING
        )

        assert len(pending) == 1
        assert pending[0].name == "Pending"
        assert len(running) == 1
        assert running[0].name == "Running"


class TestGetExperimentsByType:
    """Tests for ExperimentService.get_experiments_by_type()."""

    @pytest.mark.asyncio
    async def test_filters_by_type(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Filters experiments by type correctly."""
        await experiment_service.create_centralized_experiment(
            name="Centralized", config=default_config
        )
        await experiment_service.create_federated_experiment(
            name="Federated", config=default_config, n_clients=5, n_rounds=10
        )

        centralized = await experiment_service.get_experiments_by_type("centralized")
        federated = await experiment_service.get_experiments_by_type("federated")

        assert len(centralized) == 1
        assert centralized[0].name == "Centralized"
        assert len(federated) == 1
        assert federated[0].name == "Federated"

    @pytest.mark.asyncio
    async def test_invalid_type_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Invalid experiment type raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="must be 'centralized' or 'federated'"):
            await experiment_service.get_experiments_by_type("invalid")


# -----------------------------------------------------------------------------
# Test Experiment Lifecycle Operations
# -----------------------------------------------------------------------------


class TestStartExperiment:
    """Tests for ExperimentService.start_experiment()."""

    @pytest.mark.asyncio
    async def test_start_pending_experiment_success(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can start pending experiment."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        updated = await experiment_service.start_experiment(experiment.experiment_id)
        assert updated.status == ExperimentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_nonexistent_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Starting nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            await experiment_service.start_experiment("nonexistent-id")

    @pytest.mark.asyncio
    async def test_start_running_experiment_raises_error(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Starting already running experiment raises ConfigurationError."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )
        await experiment_service.start_experiment(experiment.experiment_id)

        with pytest.raises(ConfigurationError, match="Cannot start experiment"):
            await experiment_service.start_experiment(experiment.experiment_id)


class TestCompleteExperiment:
    """Tests for ExperimentService.complete_experiment()."""

    @pytest.mark.asyncio
    async def test_complete_running_experiment_success(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can complete running experiment with metrics."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )
        await experiment_service.start_experiment(experiment.experiment_id)

        updated = await experiment_service.complete_experiment(
            experiment.experiment_id,
            final_rmse=0.85,
            final_mae=0.65,
            training_time_seconds=120.0,
        )

        assert updated.status == ExperimentStatus.COMPLETED
        assert updated.metrics is not None
        assert updated.metrics.rmse == 0.85
        assert updated.metrics.mae == 0.65
        assert updated.metrics.training_time_seconds == 120.0

    @pytest.mark.asyncio
    async def test_complete_nonexistent_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Completing nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            await experiment_service.complete_experiment(
                "nonexistent-id", final_rmse=0.85, final_mae=0.65, training_time_seconds=120.0
            )

    @pytest.mark.asyncio
    async def test_complete_pending_experiment_raises_error(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Completing pending experiment raises ConfigurationError."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        with pytest.raises(ConfigurationError, match="Cannot complete experiment"):
            await experiment_service.complete_experiment(
                experiment.experiment_id,
                final_rmse=0.85,
                final_mae=0.65,
                training_time_seconds=120.0,
            )


class TestFailExperiment:
    """Tests for ExperimentService.fail_experiment()."""

    @pytest.mark.asyncio
    async def test_fail_running_experiment_success(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can mark running experiment as failed."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )
        await experiment_service.start_experiment(experiment.experiment_id)

        updated = await experiment_service.fail_experiment(experiment.experiment_id)
        assert updated.status == ExperimentStatus.FAILED

    @pytest.mark.asyncio
    async def test_fail_nonexistent_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Failing nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            await experiment_service.fail_experiment("nonexistent-id")

    @pytest.mark.asyncio
    async def test_fail_pending_experiment_raises_error(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Failing pending experiment raises ConfigurationError."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        with pytest.raises(ConfigurationError, match="Cannot fail experiment"):
            await experiment_service.fail_experiment(experiment.experiment_id)


# -----------------------------------------------------------------------------
# Test Delete Operations
# -----------------------------------------------------------------------------


class TestDeleteExperiment:
    """Tests for ExperimentService.delete_experiment()."""

    @pytest.mark.asyncio
    async def test_delete_existing_experiment(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Can delete existing experiment."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        await experiment_service.delete_experiment(experiment.experiment_id)

        with pytest.raises(EntityNotFoundError):
            await experiment_service.get_experiment_by_id(experiment.experiment_id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises_error(
        self, experiment_service: ExperimentService
    ):
        """Deleting nonexistent experiment raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            await experiment_service.delete_experiment("nonexistent-id")


class TestExperimentExists:
    """Tests for ExperimentService.experiment_exists()."""

    @pytest.mark.asyncio
    async def test_exists_true_for_existing(
        self, experiment_service: ExperimentService, default_config: Configuration
    ):
        """Returns True for existing experiment."""
        experiment = await experiment_service.create_centralized_experiment(
            name="Test", config=default_config
        )

        exists = await experiment_service.experiment_exists(experiment.experiment_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_false_for_nonexistent(
        self, experiment_service: ExperimentService
    ):
        """Returns False for nonexistent experiment."""
        exists = await experiment_service.experiment_exists("nonexistent-id")
        assert exists is False
