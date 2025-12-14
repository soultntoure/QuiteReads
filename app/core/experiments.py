"""Experiment domain entities.

This module defines the core experiment abstractions for comparing
centralized matrix factorization against federated learning approaches.
Experiments are pure domain objects - execution logic belongs in application layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app.core.configuration import Configuration
from app.core.metrics import ExperimentMetrics, PerformanceMetric
from app.utils.exceptions import ConfigurationError
from app.utils.types import AggregationStrategy, ExperimentStatus


@dataclass
class Experiment(ABC):
    """Abstract base class for all experiment types.

    Provides common interface for centralized and federated experiments,
    enabling side-by-side comparison in the research dashboard.

    Attributes:
        name: Human-readable experiment name.
        config: Hyperparameters and model settings.
        experiment_id: Unique identifier (auto-generated).
        status: Current experiment status.
        metrics: Final performance metrics (populated after completion).
        created_at: Timestamp when experiment was created.
        completed_at: Timestamp when experiment finished.
    """

    name: str
    config: Configuration
    experiment_id: str = field(default_factory=lambda: str(uuid4()))
    status: ExperimentStatus = ExperimentStatus.PENDING
    metrics: Optional[ExperimentMetrics] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate experiment configuration."""
        self._validate()

    def _validate(self) -> None:
        """Validate common experiment fields.

        Raises:
            ConfigurationError: If validation fails.
        """
        if not self.name or not self.name.strip():
            raise ConfigurationError("Experiment name cannot be empty")
        if len(self.name) > 100:
            raise ConfigurationError("Experiment name cannot exceed 100 characters")

    @property
    @abstractmethod
    def experiment_type(self) -> str:
        """Return the experiment type identifier."""
        ...

    @abstractmethod
    def get_training_timeline(self) -> List[PerformanceMetric]:
        """Return chronological training metrics for visualization.

        Returns:
            List of metrics captured during training (epochs or rounds).
        """
        ...

    def get_final_rmse(self) -> Optional[float]:
        """Return final RMSE if experiment completed.

        Returns:
            RMSE value or None if not completed.
        """
        return self.metrics.rmse if self.metrics else None

    def get_final_mae(self) -> Optional[float]:
        """Return final MAE if experiment completed.

        Returns:
            MAE value or None if not completed.
        """
        return self.metrics.mae if self.metrics else None

    def get_training_duration(self) -> Optional[float]:
        """Return training duration in seconds.

        Returns:
            Training time or None if not completed.
        """
        return self.metrics.training_time_seconds if self.metrics else None

    def mark_running(self) -> None:
        """Transition experiment to running state.

        Raises:
            ConfigurationError: If experiment is not in pending state.
        """
        if self.status != ExperimentStatus.PENDING:
            raise ConfigurationError(
                f"Cannot start experiment in {self.status.value} state"
            )
        self.status = ExperimentStatus.RUNNING

    def mark_completed(self, metrics: ExperimentMetrics) -> None:
        """Transition experiment to completed state with final metrics.

        Args:
            metrics: Final performance metrics.

        Raises:
            ConfigurationError: If experiment is not in running state.
        """
        if self.status != ExperimentStatus.RUNNING:
            raise ConfigurationError(
                f"Cannot complete experiment in {self.status.value} state"
            )
        self.status = ExperimentStatus.COMPLETED
        self.metrics = metrics
        self.completed_at = datetime.now()

    def mark_failed(self) -> None:
        """Transition experiment to failed state.

        Raises:
            ConfigurationError: If experiment is not in running state.
        """
        if self.status != ExperimentStatus.RUNNING:
            raise ConfigurationError(
                f"Cannot fail experiment in {self.status.value} state"
            )
        self.status = ExperimentStatus.FAILED
        self.completed_at = datetime.now()


@dataclass
class CentralizedExperiment(Experiment):
    """Centralized matrix factorization experiment (baseline).

    Trains a single global model on the full dataset without
    federated partitioning. Used as baseline for comparison.

    Attributes:
        epoch_metrics: Per-epoch training metrics (loss, RMSE).
    """

    epoch_metrics: List[PerformanceMetric] = field(default_factory=list)

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "centralized"

    def get_training_timeline(self) -> List[PerformanceMetric]:
        """Return per-epoch metrics for training visualization.

        Returns:
            List of metrics captured at each epoch.
        """
        return self.epoch_metrics

    def add_epoch_metric(self, metric: PerformanceMetric) -> None:
        """Record metric for a completed epoch.

        Args:
            metric: Performance metric for the epoch.
        """
        self.epoch_metrics.append(metric)


@dataclass
class FederatedExperiment(Experiment):
    """Federated learning experiment for recommendation.

    Simulates federated training across multiple clients,
    each holding a partition of user data. Supports various
    aggregation strategies (FedAvg, etc.).

    Attributes:
        n_clients: Number of simulated federated clients.
        n_rounds: Number of communication rounds.
        aggregation_strategy: Strategy for aggregating client updates.
        round_metrics: Per-round global model metrics.
        client_metrics: Per-client metrics for each round.
    """

    n_clients: int = 5
    n_rounds: int = 10
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FEDAVG
    round_metrics: List[PerformanceMetric] = field(default_factory=list)
    client_metrics: Dict[str, List[PerformanceMetric]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate federated-specific configuration."""
        super().__post_init__()
        self._validate_federated()

    def _validate_federated(self) -> None:
        """Validate federated experiment parameters.

        Raises:
            ConfigurationError: If validation fails.
        """
        if self.n_clients < 2:
            raise ConfigurationError("Federated experiment requires at least 2 clients")
        if self.n_clients > 100:
            raise ConfigurationError("Number of clients cannot exceed 100")
        if self.n_rounds < 1:
            raise ConfigurationError("Number of rounds must be at least 1")
        if self.n_rounds > 500:
            raise ConfigurationError("Number of rounds cannot exceed 500")

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "federated"

    def get_training_timeline(self) -> List[PerformanceMetric]:
        """Return per-round global metrics for training visualization.

        Returns:
            List of metrics captured at each communication round.
        """
        return self.round_metrics

    def add_round_metric(self, metric: PerformanceMetric) -> None:
        """Record global metric for a completed round.

        Args:
            metric: Global model performance metric for the round.
        """
        self.round_metrics.append(metric)

    def add_client_metric(self, client_id: str, metric: PerformanceMetric) -> None:
        """Record metric for a specific client in a round.

        Args:
            client_id: Identifier of the client.
            metric: Client's local performance metric.
        """
        if client_id not in self.client_metrics:
            self.client_metrics[client_id] = []
        self.client_metrics[client_id].append(metric)

    def get_client_ids(self) -> List[str]:
        """Return list of all client IDs that participated.

        Returns:
            List of client identifiers.
        """
        return list(self.client_metrics.keys())

    def get_convergence_by_round(self) -> List[float]:
        """Extract RMSE values per round for convergence analysis.

        Returns:
            List of RMSE values, one per round.
        """
        return [m.value for m in self.round_metrics if m.name == "rmse"]

    def get_client_contribution_variance(self) -> Optional[float]:
        """Calculate variance in client contributions (data heterogeneity indicator).

        Returns:
            Variance of client metric counts, or None if no client data.
        """
        if not self.client_metrics:
            return None
        counts = [len(metrics) for metrics in self.client_metrics.values()]
        if len(counts) < 2:
            return None
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        return variance
