"""
Metrics Service 

Handles business logic for performance metrics operations.
Coordinates between API layer and repository layer.
"""

from typing import Any, Dict, List, Optional

from app.core.metrics import PerformanceMetric
from app.core.repositories import IExperimentRepository, IMetricsRepository
from app.utils.exceptions import ConfigurationError, EntityNotFoundError


class MetricsService:
    """
    Service for managing performance metrics business logic.

    Responsibilities:
    - Add metrics to experiments
    - Retrieve metrics with various filters
    - Calculate aggregate statistics
    - Batch operations for metrics
    """

    def __init__(
        self,
        metrics_repository: IMetricsRepository,
        experiment_repository: IExperimentRepository,
    ):
        self._metrics_repo = metrics_repository
        self._experiment_repo = experiment_repository

    async def add_metric(
        self,
        experiment_id: str,
        name: str,
        value: float,
        context: Optional[str] = None,
        round_number: Optional[int] = None,
        client_id: Optional[str] = None,
    ) -> PerformanceMetric:
        """
        Add a performance metric to an experiment.

        Args:
            experiment_id: Experiment UUID
            name: Metric name (e.g., 'rmse', 'mae', 'loss')
            value: Metric value
            context: Optional context (e.g., 'global', 'client_1')
            round_number: Optional round number for federated experiments
            client_id: Optional client ID for federated experiments

        Returns:
            Created PerformanceMetric

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If metric data is invalid
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        if not name or not name.strip():
            raise ConfigurationError("Metric name cannot be empty")

        metric = PerformanceMetric(
            name=name,
            value=value,
            experiment_id=experiment_id,
            context=context,
            round_number=round_number,
            client_id=client_id,
        )

        await self._metrics_repo.add(metric)
        return metric

    async def add_metrics_batch(
        self, experiment_id: str, metrics: List[PerformanceMetric]
    ) -> List[PerformanceMetric]:
        """
        Add multiple metrics to an experiment in a batch.

        Args:
            experiment_id: Experiment UUID
            metrics: List of PerformanceMetric entities

        Returns:
            List of added metrics

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If metrics list is empty or invalid
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        if not metrics:
            raise ConfigurationError("Metrics list cannot be empty")

        for metric in metrics:
            if metric.experiment_id != experiment_id:
                raise ConfigurationError(
                    f"Metric experiment_id {metric.experiment_id} does not match "
                    f"expected experiment_id {experiment_id}"
                )

        await self._metrics_repo.add_batch(metrics)
        return metrics

    async def get_experiment_metrics(self, experiment_id: str) -> List[PerformanceMetric]:
        """
        Retrieve all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID

        Returns:
            List of metrics for the experiment

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        return await self._metrics_repo.get_by_experiment(experiment_id)

    async def get_metrics_by_name(
        self, experiment_id: str, metric_name: str
    ) -> List[PerformanceMetric]:
        """
        Retrieve metrics for an experiment filtered by metric name.

        Args:
            experiment_id: Experiment UUID
            metric_name: Name of the metric (e.g., 'rmse', 'mae')

        Returns:
            List of metrics with the specified name

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        return await self._metrics_repo.get_by_experiment_and_name(
            experiment_id, metric_name
        )

    async def get_client_metrics(
        self, experiment_id: str, client_id: str
    ) -> List[PerformanceMetric]:
        """
        Retrieve metrics for a specific client in a federated experiment.

        Args:
            experiment_id: Experiment UUID
            client_id: Client ID

        Returns:
            List of metrics for the specified client

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        return await self._metrics_repo.get_client_metrics(experiment_id, client_id)

    async def get_round_metrics(
        self, experiment_id: str, round_number: int
    ) -> List[PerformanceMetric]:
        """
        Retrieve metrics for a specific round in a federated experiment.

        Args:
            experiment_id: Experiment UUID
            round_number: Round number

        Returns:
            List of metrics for the specified round

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If round_number is invalid
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        if round_number < 0:
            raise ConfigurationError("round_number must be non-negative")

        return await self._metrics_repo.get_round_metrics(experiment_id, round_number)

    async def get_metric_statistics(
        self, experiment_id: str, metric_name: str
    ) -> Dict[str, float]:
        """
        Calculate aggregate statistics for a specific metric.

        Args:
            experiment_id: Experiment UUID
            metric_name: Name of the metric

        Returns:
            Dictionary with keys: 'min', 'max', 'avg', 'count'

        Raises:
            EntityNotFoundError: If experiment not found or no metrics found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        stats = await self._metrics_repo.get_metric_stats(experiment_id, metric_name)
        if stats is None:
            raise EntityNotFoundError(
                f"No metrics found for experiment {experiment_id} "
                f"with name '{metric_name}'"
            )

        return stats
    
    

    async def calculate_final_metrics(
        self, experiment_id: str
    ) -> Dict[str, float]:
        """
        Calculate final RMSE and MAE from all training metrics.

        Uses the last recorded values for each metric as the final metrics.
        This should be called before completing an experiment.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Dictionary with keys: 'rmse', 'mae'

        Raises:
            EntityNotFoundError: If experiment not found or no metrics found
            ConfigurationError: If required metrics (rmse, mae) are missing
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        # Get all metrics for the experiment
        all_metrics = await self._metrics_repo.get_by_experiment(experiment_id)

        if not all_metrics:
            raise EntityNotFoundError(
                f"No metrics found for experiment {experiment_id}"
            )

        # Group metrics by name
        metrics_by_name: Dict[str, List[PerformanceMetric]] = {}
        for metric in all_metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)

        # Get the last RMSE value (assuming metrics are ordered by round/epoch)
        if "rmse" not in metrics_by_name:
            raise ConfigurationError(
                f"No RMSE metrics found for experiment {experiment_id}"
            )

        if "mae" not in metrics_by_name:
            raise ConfigurationError(
                f"No MAE metrics found for experiment {experiment_id}"
            )

        # Sort by round_number (if present) to get the last value
        rmse_metrics = sorted(
            metrics_by_name["rmse"],
            key=lambda m: m.round_number or 0
        )
        mae_metrics = sorted(
            metrics_by_name["mae"],
            key=lambda m: m.round_number or 0
        )

        final_rmse = rmse_metrics[-1].value
        final_mae = mae_metrics[-1].value

        return {
            "rmse": final_rmse,
            "mae": final_mae,
        }

    async def delete_experiment_metrics(self, experiment_id: str) -> None:
        """
        Delete all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        await self._metrics_repo.delete_by_experiment(experiment_id)

    async def get_convergence_analysis(
        self, experiment_id: str, metric_name: str = "rmse"
    ) -> List[Dict[str, Any]]:
        """
        Get convergence analysis by retrieving metrics ordered by round.

        Args:
            experiment_id: Experiment UUID
            metric_name: Metric to analyze (default: 'rmse')

        Returns:
            List of dicts with 'round_number' and 'value' keys

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        metrics = await self._metrics_repo.get_by_experiment_and_name(
            experiment_id, metric_name
        )

        metrics_with_rounds = [m for m in metrics if m.round_number is not None]
        metrics_with_rounds.sort(key=lambda m: m.round_number or 0)

        return [
            {"round_number": m.round_number, "value": m.value}
            for m in metrics_with_rounds
        ]

    async def get_client_performance_comparison(
        self, experiment_id: str, metric_name: str = "rmse"
    ) -> Dict[str, float]:
        """
        Compare average performance across all clients.

        Args:
            experiment_id: Experiment UUID
            metric_name: Metric to compare (default: 'rmse')

        Returns:
            Dictionary mapping client_id to average metric value

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        metrics = await self._metrics_repo.get_by_experiment_and_name(
            experiment_id, metric_name
        )

        client_metrics: Dict[str, List[float]] = {}
        for metric in metrics:
            if metric.client_id is not None:
                if metric.client_id not in client_metrics:
                    client_metrics[metric.client_id] = []
                client_metrics[metric.client_id].append(metric.value)

        return {
            client_id: sum(values) / len(values)
            for client_id, values in client_metrics.items()
            if values
        }
