"""Unit tests for experiment domain entities.

Tests cover:
- Experiment ABC validation and state transitions
- CentralizedExperiment creation and metrics tracking
- FederatedExperiment creation, validation, and FL-specific methods
"""

import pytest
from datetime import datetime

from app.core.configuration import Configuration
from app.core.experiments import (
    CentralizedExperiment,
    Experiment,
    FederatedExperiment,
)
from app.core.metrics import ExperimentMetrics, PerformanceMetric
from app.utils.exceptions import ConfigurationError
from app.utils.types import AggregationStrategy, ExperimentStatus


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def default_config() -> Configuration:
    """Create default configuration for tests."""
    return Configuration(n_factors=20, n_epochs=10)


@pytest.fixture
def centralized_experiment(default_config: Configuration) -> CentralizedExperiment:
    """Create a centralized experiment for tests."""
    return CentralizedExperiment(name="Test Baseline", config=default_config)


@pytest.fixture
def federated_experiment(default_config: Configuration) -> FederatedExperiment:
    """Create a federated experiment for tests."""
    return FederatedExperiment(
        name="Test Federated",
        config=default_config,
        n_clients=5,
        n_rounds=10,
    )


@pytest.fixture
def completed_metrics() -> ExperimentMetrics:
    """Create sample completed metrics."""
    return ExperimentMetrics(
        rmse=0.85,
        mae=0.65,
        training_time_seconds=120.5,
    )


# -----------------------------------------------------------------------------
# Experiment ABC Tests
# -----------------------------------------------------------------------------


class TestExperimentABC:
    """Tests for abstract Experiment base class behavior."""

    def test_cannot_instantiate_abc(self, default_config: Configuration) -> None:
        """Experiment ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Experiment(name="Test", config=default_config)  # type: ignore

    def test_experiment_generates_unique_id(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Each experiment gets a unique ID."""
        exp2 = CentralizedExperiment(
            name="Another", config=centralized_experiment.config
        )
        assert centralized_experiment.experiment_id != exp2.experiment_id

    def test_experiment_default_status_is_pending(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """New experiments start in PENDING status."""
        assert centralized_experiment.status == ExperimentStatus.PENDING

    def test_experiment_created_at_is_set(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Experiment creation timestamp is set automatically."""
        assert centralized_experiment.created_at is not None
        assert isinstance(centralized_experiment.created_at, datetime)

    def test_experiment_completed_at_is_none_initially(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Experiment completed_at is None before completion."""
        assert centralized_experiment.completed_at is None


class TestExperimentValidation:
    """Tests for experiment validation rules."""

    def test_empty_name_raises_error(self, default_config: Configuration) -> None:
        """Empty experiment name raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="name cannot be empty"):
            CentralizedExperiment(name="", config=default_config)

    def test_whitespace_name_raises_error(self, default_config: Configuration) -> None:
        """Whitespace-only name raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="name cannot be empty"):
            CentralizedExperiment(name="   ", config=default_config)

    def test_name_exceeds_max_length_raises_error(
        self, default_config: Configuration
    ) -> None:
        """Name exceeding 100 characters raises ConfigurationError."""
        long_name = "x" * 101
        with pytest.raises(ConfigurationError, match="cannot exceed 100 characters"):
            CentralizedExperiment(name=long_name, config=default_config)

    def test_valid_name_at_max_length(self, default_config: Configuration) -> None:
        """Name exactly at 100 characters is valid."""
        name = "x" * 100
        exp = CentralizedExperiment(name=name, config=default_config)
        assert exp.name == name


class TestExperimentStateTransitions:
    """Tests for experiment state machine transitions."""

    def test_mark_running_from_pending(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Can transition from PENDING to RUNNING."""
        centralized_experiment.mark_running()
        assert centralized_experiment.status == ExperimentStatus.RUNNING

    def test_mark_running_from_running_raises_error(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Cannot transition from RUNNING to RUNNING."""
        centralized_experiment.mark_running()
        with pytest.raises(ConfigurationError, match="Cannot start experiment"):
            centralized_experiment.mark_running()

    def test_mark_running_from_completed_raises_error(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """Cannot transition from COMPLETED to RUNNING."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        with pytest.raises(ConfigurationError, match="Cannot start experiment"):
            centralized_experiment.mark_running()

    def test_mark_completed_from_running(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """Can transition from RUNNING to COMPLETED."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        assert centralized_experiment.status == ExperimentStatus.COMPLETED
        assert centralized_experiment.metrics == completed_metrics

    def test_mark_completed_sets_completed_at(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """Completing experiment sets completed_at timestamp."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        assert centralized_experiment.completed_at is not None

    def test_mark_completed_from_pending_raises_error(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """Cannot transition from PENDING to COMPLETED."""
        with pytest.raises(ConfigurationError, match="Cannot complete experiment"):
            centralized_experiment.mark_completed(completed_metrics)

    def test_mark_failed_from_running(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Can transition from RUNNING to FAILED."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_failed()
        assert centralized_experiment.status == ExperimentStatus.FAILED

    def test_mark_failed_sets_completed_at(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Failing experiment sets completed_at timestamp."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_failed()
        assert centralized_experiment.completed_at is not None

    def test_mark_failed_from_pending_raises_error(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Cannot transition from PENDING to FAILED."""
        with pytest.raises(ConfigurationError, match="Cannot fail experiment"):
            centralized_experiment.mark_failed()


class TestExperimentMetricAccessors:
    """Tests for experiment metric accessor methods."""

    def test_get_final_rmse_returns_none_before_completion(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """get_final_rmse returns None before experiment completes."""
        assert centralized_experiment.get_final_rmse() is None

    def test_get_final_rmse_returns_value_after_completion(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """get_final_rmse returns correct value after completion."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        assert centralized_experiment.get_final_rmse() == 0.85

    def test_get_final_mae_returns_none_before_completion(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """get_final_mae returns None before experiment completes."""
        assert centralized_experiment.get_final_mae() is None

    def test_get_final_mae_returns_value_after_completion(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """get_final_mae returns correct value after completion."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        assert centralized_experiment.get_final_mae() == 0.65

    def test_get_training_duration_returns_none_before_completion(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """get_training_duration returns None before completion."""
        assert centralized_experiment.get_training_duration() is None

    def test_get_training_duration_returns_value_after_completion(
        self,
        centralized_experiment: CentralizedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """get_training_duration returns correct value after completion."""
        centralized_experiment.mark_running()
        centralized_experiment.mark_completed(completed_metrics)
        assert centralized_experiment.get_training_duration() == 120.5


# -----------------------------------------------------------------------------
# CentralizedExperiment Tests
# -----------------------------------------------------------------------------


class TestCentralizedExperiment:
    """Tests for CentralizedExperiment class."""

    def test_experiment_type_is_centralized(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """experiment_type property returns 'centralized'."""
        assert centralized_experiment.experiment_type == "centralized"

    def test_epoch_metrics_empty_initially(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """epoch_metrics list is empty on creation."""
        assert centralized_experiment.epoch_metrics == []

    def test_add_epoch_metric(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Can add epoch metrics."""
        metric = PerformanceMetric(
            name="rmse",
            value=0.95,
            experiment_id=centralized_experiment.experiment_id,
            round_number=1,
        )
        centralized_experiment.add_epoch_metric(metric)
        assert len(centralized_experiment.epoch_metrics) == 1
        assert centralized_experiment.epoch_metrics[0] == metric

    def test_add_multiple_epoch_metrics(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """Can add multiple epoch metrics."""
        for i in range(5):
            metric = PerformanceMetric(
                name="rmse",
                value=1.0 - i * 0.1,
                experiment_id=centralized_experiment.experiment_id,
                round_number=i,
            )
            centralized_experiment.add_epoch_metric(metric)
        assert len(centralized_experiment.epoch_metrics) == 5

    def test_get_training_timeline_returns_epoch_metrics(
        self, centralized_experiment: CentralizedExperiment
    ) -> None:
        """get_training_timeline returns epoch_metrics."""
        metric = PerformanceMetric(
            name="rmse",
            value=0.9,
            experiment_id=centralized_experiment.experiment_id,
            round_number=1,
        )
        centralized_experiment.add_epoch_metric(metric)
        timeline = centralized_experiment.get_training_timeline()
        assert timeline == centralized_experiment.epoch_metrics


# -----------------------------------------------------------------------------
# FederatedExperiment Tests
# -----------------------------------------------------------------------------


class TestFederatedExperiment:
    """Tests for FederatedExperiment class."""

    def test_experiment_type_is_federated(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """experiment_type property returns 'federated'."""
        assert federated_experiment.experiment_type == "federated"

    def test_default_aggregation_strategy(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """Default aggregation strategy is FEDAVG."""
        assert federated_experiment.aggregation_strategy == AggregationStrategy.FEDAVG

    def test_round_metrics_empty_initially(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """round_metrics list is empty on creation."""
        assert federated_experiment.round_metrics == []

    def test_client_metrics_empty_initially(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """client_metrics dict is empty on creation."""
        assert federated_experiment.client_metrics == {}


class TestFederatedExperimentValidation:
    """Tests for FederatedExperiment validation rules."""

    def test_n_clients_less_than_2_raises_error(
        self, default_config: Configuration
    ) -> None:
        """n_clients < 2 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="at least 2 clients"):
            FederatedExperiment(
                name="Test", config=default_config, n_clients=1, n_rounds=10
            )

    def test_n_clients_exceeds_max_raises_error(
        self, default_config: Configuration
    ) -> None:
        """n_clients > 100 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="cannot exceed 100"):
            FederatedExperiment(
                name="Test", config=default_config, n_clients=101, n_rounds=10
            )

    def test_n_rounds_less_than_1_raises_error(
        self, default_config: Configuration
    ) -> None:
        """n_rounds < 1 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="at least 1"):
            FederatedExperiment(
                name="Test", config=default_config, n_clients=5, n_rounds=0
            )

    def test_n_rounds_exceeds_max_raises_error(
        self, default_config: Configuration
    ) -> None:
        """n_rounds > 500 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="cannot exceed 500"):
            FederatedExperiment(
                name="Test", config=default_config, n_clients=5, n_rounds=501
            )

    def test_valid_boundary_values(self, default_config: Configuration) -> None:
        """Boundary values (2 clients, 1 round) are valid."""
        exp = FederatedExperiment(
            name="Test", config=default_config, n_clients=2, n_rounds=1
        )
        assert exp.n_clients == 2
        assert exp.n_rounds == 1


class TestFederatedExperimentMetrics:
    """Tests for FederatedExperiment metric methods."""

    def test_add_round_metric(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """Can add round metrics."""
        metric = PerformanceMetric(
            name="rmse",
            value=0.9,
            experiment_id=federated_experiment.experiment_id,
            round_number=1,
        )
        federated_experiment.add_round_metric(metric)
        assert len(federated_experiment.round_metrics) == 1

    def test_get_training_timeline_returns_round_metrics(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_training_timeline returns round_metrics."""
        metric = PerformanceMetric(
            name="rmse",
            value=0.9,
            experiment_id=federated_experiment.experiment_id,
            round_number=1,
        )
        federated_experiment.add_round_metric(metric)
        timeline = federated_experiment.get_training_timeline()
        assert timeline == federated_experiment.round_metrics

    def test_add_client_metric_creates_client_entry(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """Adding client metric creates client entry if not exists."""
        metric = PerformanceMetric(
            name="loss",
            value=0.5,
            experiment_id=federated_experiment.experiment_id,
            client_id="client_1",
        )
        federated_experiment.add_client_metric("client_1", metric)
        assert "client_1" in federated_experiment.client_metrics

    def test_add_client_metric_appends_to_existing(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """Adding client metric appends to existing client list."""
        metric1 = PerformanceMetric(
            name="loss",
            value=0.5,
            experiment_id=federated_experiment.experiment_id,
            round_number=1,
        )
        metric2 = PerformanceMetric(
            name="loss",
            value=0.4,
            experiment_id=federated_experiment.experiment_id,
            round_number=2,
        )
        federated_experiment.add_client_metric("client_1", metric1)
        federated_experiment.add_client_metric("client_1", metric2)
        assert len(federated_experiment.client_metrics["client_1"]) == 2

    def test_get_client_ids_returns_all_clients(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_client_ids returns all participating client IDs."""
        for i in range(3):
            metric = PerformanceMetric(
                name="loss",
                value=0.5,
                experiment_id=federated_experiment.experiment_id,
            )
            federated_experiment.add_client_metric(f"client_{i}", metric)
        client_ids = federated_experiment.get_client_ids()
        assert len(client_ids) == 3
        assert "client_0" in client_ids
        assert "client_1" in client_ids
        assert "client_2" in client_ids

    def test_get_convergence_by_round(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_convergence_by_round extracts RMSE values."""
        for i in range(5):
            rmse = PerformanceMetric(
                name="rmse",
                value=1.0 - i * 0.1,
                experiment_id=federated_experiment.experiment_id,
                round_number=i,
            )
            loss = PerformanceMetric(
                name="loss",
                value=0.5,
                experiment_id=federated_experiment.experiment_id,
                round_number=i,
            )
            federated_experiment.add_round_metric(rmse)
            federated_experiment.add_round_metric(loss)
        convergence = federated_experiment.get_convergence_by_round()
        assert len(convergence) == 5
        assert convergence[0] == 1.0
        assert convergence[4] == 0.6

    def test_get_client_contribution_variance_returns_none_no_data(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_client_contribution_variance returns None with no data."""
        assert federated_experiment.get_client_contribution_variance() is None

    def test_get_client_contribution_variance_returns_none_single_client(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_client_contribution_variance returns None with single client."""
        metric = PerformanceMetric(
            name="loss",
            value=0.5,
            experiment_id=federated_experiment.experiment_id,
        )
        federated_experiment.add_client_metric("client_1", metric)
        assert federated_experiment.get_client_contribution_variance() is None

    def test_get_client_contribution_variance_calculates_correctly(
        self, federated_experiment: FederatedExperiment
    ) -> None:
        """get_client_contribution_variance calculates variance correctly."""
        # Client 1: 2 metrics, Client 2: 4 metrics
        # Counts: [2, 4], Mean: 3, Variance: ((2-3)^2 + (4-3)^2) / 2 = 1
        for _ in range(2):
            federated_experiment.add_client_metric(
                "client_1",
                PerformanceMetric(
                    name="loss",
                    value=0.5,
                    experiment_id=federated_experiment.experiment_id,
                ),
            )
        for _ in range(4):
            federated_experiment.add_client_metric(
                "client_2",
                PerformanceMetric(
                    name="loss",
                    value=0.5,
                    experiment_id=federated_experiment.experiment_id,
                ),
            )
        variance = federated_experiment.get_client_contribution_variance()
        assert variance == 1.0


# -----------------------------------------------------------------------------
# Polymorphism Tests
# -----------------------------------------------------------------------------


class TestPolymorphism:
    """Tests for polymorphic behavior across experiment types."""

    def test_both_types_share_common_interface(
        self,
        centralized_experiment: CentralizedExperiment,
        federated_experiment: FederatedExperiment,
        completed_metrics: ExperimentMetrics,
    ) -> None:
        """Both experiment types can be used interchangeably via common interface."""
        experiments: list[Experiment] = [centralized_experiment, federated_experiment]

        for exp in experiments:
            # Common operations work on both
            assert exp.status == ExperimentStatus.PENDING
            assert exp.get_final_rmse() is None

            exp.mark_running()
            assert exp.status == ExperimentStatus.RUNNING

            exp.mark_completed(completed_metrics)
            assert exp.get_final_rmse() == 0.85
            assert exp.get_final_mae() == 0.65

    def test_experiment_type_distinguishes_subclasses(
        self,
        centralized_experiment: CentralizedExperiment,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """experiment_type property distinguishes experiment types."""
        assert centralized_experiment.experiment_type == "centralized"
        assert federated_experiment.experiment_type == "federated"

    def test_get_training_timeline_returns_type_specific_data(
        self,
        centralized_experiment: CentralizedExperiment,
        federated_experiment: FederatedExperiment,
    ) -> None:
        """get_training_timeline returns appropriate metrics per type."""
        epoch_metric = PerformanceMetric(
            name="rmse",
            value=0.9,
            experiment_id=centralized_experiment.experiment_id,
            round_number=1,
        )
        round_metric = PerformanceMetric(
            name="rmse",
            value=0.85,
            experiment_id=federated_experiment.experiment_id,
            round_number=1,
        )

        centralized_experiment.add_epoch_metric(epoch_metric)
        federated_experiment.add_round_metric(round_metric)

        assert centralized_experiment.get_training_timeline() == [epoch_metric]
        assert federated_experiment.get_training_timeline() == [round_metric]