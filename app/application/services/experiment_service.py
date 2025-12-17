"""
Experiment Service Layer

Handles business logic for experiment operations.
implements use cases for experiments/metrics.
"""

from datetime import datetime
from typing import List
from uuid import uuid4

from app.core.configuration import Configuration
from app.core.experiments import (
    CentralizedExperiment,
    Experiment,
    ExperimentMetrics,
    FederatedExperiment,
)
from app.core.metrics import PerformanceMetric
from app.domain.repositories import IExperimentRepository, IMetricsRepository
from app.utils.exceptions import ConfigurationError, EntityNotFoundError
from app.utils.types import AggregationStrategy, ExperimentStatus


class ExperimentService:
    """
    Service for managing experiment business logic.

    Responsibilities:
    - Create experiments (centralized/federated)
    - Update experiment lifecycle (running, completed, failed)
    - Retrieve experiments by various filters
    - Coordinate between experiment and metrics repositories
    """

    def __init__(
        self,
        experiment_repository: IExperimentRepository,
        metrics_repository: IMetricsRepository,
    ):
        self._experiment_repo = experiment_repository
        self._metrics_repo = metrics_repository

    async def create_centralized_experiment(
        self,
        name: str,
        config: Configuration,
    ) -> CentralizedExperiment:
        """
        Create a new centralized experiment.

        Args:
            name: Experiment name
            config: Experiment configuration

        Returns:
            Created CentralizedExperiment

        Raises:
            ConfigurationError: If configuration is invalid
        """
        experiment = CentralizedExperiment(
            experiment_id=str(uuid4()),
            name=name,
            config=config,
            status=ExperimentStatus.PENDING,
            created_at=datetime.now(),
        )

        await self._experiment_repo.add(experiment)
        return experiment

    async def create_federated_experiment(
        self,
        name: str,
        config: Configuration,
        n_clients: int,
        n_rounds: int,
        aggregation_strategy: AggregationStrategy = AggregationStrategy.FEDAVG,
    ) -> FederatedExperiment:
        """
        Create a new federated experiment.

        Args:
            name: Experiment name
            config: Experiment configuration
            n_clients: Number of federated clients
            n_rounds: Number of federated rounds
            aggregation_strategy: Aggregation strategy (default: FEDAVG)

        Returns:
            Created FederatedExperiment

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if n_clients < 2 or n_clients > 100:
            raise ConfigurationError("n_clients must be between 2 and 100")
        if n_rounds < 1 or n_rounds > 500:
            raise ConfigurationError("n_rounds must be between 1 and 500")

        experiment = FederatedExperiment(
            experiment_id=str(uuid4()),
            name=name,
            config=config,
            n_clients=n_clients,
            n_rounds=n_rounds,
            aggregation_strategy=aggregation_strategy,
            status=ExperimentStatus.PENDING,
            created_at=datetime.now(),
        )

        await self._experiment_repo.add(experiment)
        return experiment

    async def get_experiment_by_id(self, experiment_id: str) -> Experiment:
        """
        Retrieve an experiment by ID.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Experiment entity

        Raises:
            EntityNotFoundError: If experiment not found
        """
        experiment = await self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")
        return experiment

    async def get_all_experiments(self) -> List[Experiment]:
        """
        Retrieve all experiments.

        Returns:
            List of all experiments
        """
        return await self._experiment_repo.get_all()

    async def get_experiments_by_status(
        self, status: ExperimentStatus
    ) -> List[Experiment]:
        """
        Retrieve experiments by status.

        Args:
            status: Experiment status to filter by

        Returns:
            List of experiments with the given status
        """
        return await self._experiment_repo.get_by_status(status)

    async def get_experiments_by_type(self, experiment_type: str) -> List[Experiment]:
        """
        Retrieve experiments by type.

        Args:
            experiment_type: "centralized" or "federated"

        Returns:
            List of experiments of the given type

        Raises:
            ConfigurationError: If experiment_type is invalid
        """
        if experiment_type not in ["centralized", "federated"]:
            raise ConfigurationError(
                "experiment_type must be 'centralized' or 'federated'"
            )
        return await self._experiment_repo.get_by_type(experiment_type)

    async def start_experiment(self, experiment_id: str) -> Experiment:
        """
        Mark an experiment as running.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Updated experiment

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If experiment is not in PENDING status
        """
        experiment = await self.get_experiment_by_id(experiment_id)

        if experiment.status != ExperimentStatus.PENDING:
            raise ConfigurationError(
                f"Cannot start experiment with status {experiment.status.value}. "
                "Only PENDING experiments can be started."
            )

        experiment.mark_running()
        await self._experiment_repo.update(experiment)
        return experiment

    async def complete_experiment(
        self,
        experiment_id: str,
        final_rmse: float,
        final_mae: float,
        training_time_seconds: float,
    ) -> Experiment:
        """
        Mark an experiment as completed with final metrics.

        Args:
            experiment_id: Experiment UUID
            final_rmse: Final RMSE metric
            final_mae: Final MAE metric
            training_time_seconds: Total training time

        Returns:
            Updated experiment

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If experiment is not in RUNNING status
        """
        experiment = await self.get_experiment_by_id(experiment_id)

        if experiment.status != ExperimentStatus.RUNNING:
            raise ConfigurationError(
                f"Cannot complete experiment with status {experiment.status.value}. "
                "Only RUNNING experiments can be completed."
            )

        metrics = ExperimentMetrics(
            rmse=final_rmse,
            mae=final_mae,
            training_time_seconds=training_time_seconds,
        )

        experiment.mark_completed(metrics)
        await self._experiment_repo.update(experiment)
        return experiment

    async def fail_experiment(self, experiment_id: str) -> Experiment:
        """
        Mark an experiment as failed.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Updated experiment

        Raises:
            EntityNotFoundError: If experiment not found
            ConfigurationError: If experiment is not in RUNNING status
        """
        experiment = await self.get_experiment_by_id(experiment_id)

        if experiment.status != ExperimentStatus.RUNNING:
            raise ConfigurationError(
                f"Cannot fail experiment with status {experiment.status.value}. "
                "Only RUNNING experiments can be marked as failed."
            )

        experiment.mark_failed()
        await self._experiment_repo.update(experiment)
        return experiment

    async def delete_experiment(self, experiment_id: str) -> None:
        """
        Delete an experiment and all associated metrics.

        Args:
            experiment_id: Experiment UUID

        Raises:
            EntityNotFoundError: If experiment not found
        """
        exists = await self._experiment_repo.exists(experiment_id)
        if not exists:
            raise EntityNotFoundError(f"Experiment with id {experiment_id} not found")

        await self._metrics_repo.delete_by_experiment(experiment_id)
        await self._experiment_repo.delete(experiment_id)

    async def experiment_exists(self, experiment_id: str) -> bool:
        """
        Check if an experiment exists.

        Args:
            experiment_id: Experiment UUID

        Returns:
            True if experiment exists, False otherwise
        """
        return await self._experiment_repo.exists(experiment_id)
