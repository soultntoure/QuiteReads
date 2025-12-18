"""Repository interface protocols.

Defines abstract interfaces for repositories using typing.Protocol.
This enables dependency inversion: services depend on these interfaces,
not on concrete repository implementations.

Following SOLID principles:
- Dependency Inversion: High-level modules (services) depend on abstractions
- Interface Segregation: Protocols define only methods actually used
"""

from typing import Dict, List, Optional, Protocol

from app.core.experiments import Experiment
from app.core.metrics import PerformanceMetric
from app.utils.types import ExperimentStatus


class IExperimentRepository(Protocol):
    """Interface for experiment repository.

    Defines the contract for experiment persistence operations.
    Services depend on this interface, not the concrete implementation.
    """

    async def add(self, entity: Experiment) -> Experiment:
        """Persist a new experiment.

        Args:
            entity: Experiment domain entity.

        Returns:
            The persisted experiment.

        Raises:
            RepositoryError: If persistence fails.
        """
        ...

    async def get_by_id(self, entity_id: str) -> Optional[Experiment]:
        """Retrieve an experiment by ID.

        Args:
            entity_id: Experiment UUID.

        Returns:
            Experiment if found, None otherwise.
        """
        ...

    async def get_all(self) -> List[Experiment]:
        """Retrieve all experiments.

        Returns:
            List of all experiments.
        """
        ...

    async def get_by_status(self, status: ExperimentStatus) -> List[Experiment]:
        """Retrieve experiments by status.

        Args:
            status: Experiment status to filter by.

        Returns:
            List of experiments with given status.
        """
        ...

    async def get_by_type(self, experiment_type: str) -> List[Experiment]:
        """Retrieve experiments by type.

        Args:
            experiment_type: 'centralized' or 'federated'.

        Returns:
            List of experiments of given type.
        """
        ...

    async def update(self, entity: Experiment) -> Experiment:
        """Update an existing experiment.

        Args:
            entity: Experiment with updated fields.

        Returns:
            Updated experiment.

        Raises:
            EntityNotFoundError: If experiment not found.
            RepositoryError: If update fails.
        """
        ...

    async def delete(self, entity_id: str) -> bool:
        """Delete an experiment by ID.

        Args:
            entity_id: Experiment UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def exists(self, entity_id: str) -> bool:
        """Check if experiment exists.

        Args:
            entity_id: Experiment UUID.

        Returns:
            True if exists, False otherwise.
        """
        ...


class IMetricsRepository(Protocol):
    """Interface for metrics repository.

    Defines the contract for performance metrics persistence and querying.
    Services depend on this interface, not the concrete implementation.
    """

    async def add(self, entity: PerformanceMetric) -> PerformanceMetric:
        """Persist a new metric.

        Args:
            entity: PerformanceMetric to persist.

        Returns:
            The persisted metric.

        Raises:
            RepositoryError: If persistence fails.
        """
        ...

    async def add_batch(
        self, metrics: List[PerformanceMetric]
    ) -> List[PerformanceMetric]:
        """Persist multiple metrics in batch.

        Args:
            metrics: List of metrics to persist.

        Returns:
            List of persisted metrics.

        Raises:
            RepositoryError: If persistence fails.
        """
        ...

    async def get_by_experiment(self, experiment_id: str) -> List[PerformanceMetric]:
        """Retrieve all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            List of metrics for the experiment.
        """
        ...

    async def get_by_experiment_and_name(
        self, experiment_id: str, metric_name: str
    ) -> List[PerformanceMetric]:
        """Retrieve metrics by experiment and metric name.

        Args:
            experiment_id: Experiment UUID.
            metric_name: Name of metric (e.g., 'rmse', 'loss').

        Returns:
            List of matching metrics.
        """
        ...

    async def get_client_metrics(
        self, experiment_id: str, client_id: str
    ) -> List[PerformanceMetric]:
        """Retrieve metrics for a specific client.

        Args:
            experiment_id: Experiment UUID.
            client_id: Client identifier.

        Returns:
            List of metrics for the client.
        """
        ...

    async def get_round_metrics(
        self, experiment_id: str, round_number: int
    ) -> List[PerformanceMetric]:
        """Retrieve metrics for a specific round.

        Args:
            experiment_id: Experiment UUID.
            round_number: Communication round number.

        Returns:
            List of metrics for the round.
        """
        ...

    async def get_metric_stats(
        self, experiment_id: str, metric_name: str
    ) -> Dict[str, float]:
        """Get aggregate statistics for a metric.

        Args:
            experiment_id: Experiment UUID.
            metric_name: Name of metric.

        Returns:
            Dict with min, max, avg, count.
        """
        ...

    async def delete_by_experiment(self, experiment_id: str) -> int:
        """Delete all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            Number of metrics deleted.
        """
        ...
