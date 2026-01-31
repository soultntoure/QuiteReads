"""Experiment manager for orchestrating training experiments.

Coordinates between training modules, services, and data loading to run
complete experiments (centralized or federated) with proper lifecycle
management and metrics persistence.
"""

import logging
from pathlib import Path
from typing import Optional

from app.application.data.dataset_loader import DatasetLoader
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.application.training.centralized_trainer import CentralizedTrainer, TrainingResult
from app.application.training.federated_simulation_manager import (
    FederatedSimulationManager,
    FederatedSimulationResult,
)
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.core.metrics import PerformanceMetric
from app.utils.types import AggregationStrategy

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Orchestrates experiment execution and lifecycle management.

    Coordinates:
    - Data loading via DatasetLoader
    - Training via CentralizedTrainer (or FederatedSimulationManager)
    - Persistence via ExperimentService and MetricsService
    - State transitions (PENDING -> RUNNING -> COMPLETED/FAILED)

    Example:
        >>> manager = ExperimentManager(
        ...     experiment_service=exp_service,
        ...     metrics_service=metrics_service,
        ...     data_dir=Path("data"),
        ... )
        >>> experiment = await manager.run_centralized_experiment(
        ...     name="Baseline Run",
        ...     config=Configuration(n_factors=50, n_epochs=20),
        ... )
        >>> print(f"RMSE: {experiment.get_final_rmse()}")
    """

    def __init__(
        self,
        experiment_service: ExperimentService,
        metrics_service: MetricsService,
        data_dir: Path,
        checkpoint_dir: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
        batch_size: int = 1024,
    ):
        """Initialize the experiment manager.

        Args:
            experiment_service: Service for experiment lifecycle management.
            metrics_service: Service for metrics persistence.
            data_dir: Path to the data directory with preprocessed data.
            checkpoint_dir: Optional directory for model checkpoints.
            storage_dir: Directory for federated simulation artifacts
                (partitions, results). Defaults to data_dir / "federated".
            batch_size: Batch size for training DataLoaders.
        """
        self._experiment_service = experiment_service
        self._metrics_service = metrics_service
        self._data_dir = data_dir
        self._checkpoint_dir = checkpoint_dir
        self._storage_dir = storage_dir or (data_dir / "federated")
        self._batch_size = batch_size

        self._data_loader: Optional[DatasetLoader] = None

    def _ensure_data_loaded(self) -> DatasetLoader:
        """Ensure data is loaded and return the DatasetLoader.
        Why?:  Loading data can be expensive (reading CSV files, computing statistics). 
        If an ExperimentManager is created but no experiments are run, no data is loaded.
        """
        if self._data_loader is None:
            self._data_loader = DatasetLoader(self._data_dir)
            self._data_loader.load()
        return self._data_loader

    async def run_centralized_experiment(
        self,
        name: str,
        config: Configuration,
        accelerator: str = "auto",
    ) -> CentralizedExperiment:
        """Run a complete centralized training experiment.

        Creates the experiment, runs training, persists metrics,
        and marks the experiment as completed or failed.

        Args:
            name: Human-readable experiment name.
            config: Experiment configuration with hyperparameters.
            accelerator: Device accelerator ("auto", "cpu", "gpu").

        Returns:
            Completed CentralizedExperiment with final metrics.

        Raises:
            Exception: Propagates any training errors after marking
                experiment as failed.
        """
        # Create experiment (PENDING state)
        experiment = await self._experiment_service.create_centralized_experiment(
            name=name,
            config=config,
        )
        experiment_id = experiment.experiment_id

        logger.info(f"Created centralized experiment: {experiment_id}")

        try:
            # Transition to RUNNING
            await self._experiment_service.start_experiment(experiment_id)
            logger.info(f"Started experiment: {experiment_id}")

            # Load data
            data_loader = self._ensure_data_loaded()

            # Create DataLoaders
            train_loader = data_loader.get_train_loader(batch_size=self._batch_size)
            val_loader = data_loader.get_val_loader(batch_size=self._batch_size)

            # Initialize trainer
            trainer = CentralizedTrainer(
                config=config,
                n_users=data_loader.n_users,
                n_items=data_loader.n_items,
                global_mean=data_loader.global_mean,
                checkpoint_dir=self._checkpoint_dir,
            )

            # Run training
            logger.info(f"Starting training for {config.n_epochs} epochs")
            result = trainer.train(train_loader, val_loader, accelerator)

            # Persist per-epoch metrics to database
            await self._persist_training_metrics(experiment_id, result)

            # Complete experiment with final metrics
            experiment = await self._experiment_service.complete_experiment(
                experiment_id=experiment_id,
                final_rmse=result.final_rmse,
                final_mae=result.final_mae,
                training_time_seconds=result.training_time_seconds,
            )

            logger.info(
                f"Completed experiment {experiment_id}: "
                f"RMSE={result.final_rmse:.4f}, MAE={result.final_mae:.4f}"
            )

            return experiment

        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            await self._experiment_service.fail_experiment(experiment_id)
            raise

    async def run_federated_experiment(
        self,
        name: str,
        config: Configuration,
        n_clients: int = 10,
        n_rounds: int = 10,
        aggregation_strategy: AggregationStrategy = AggregationStrategy.FEDAVG,
        local_epochs: int = 5,
        fraction_train: float = 1.0,
        fraction_evaluate: float = 1.0,
        force_repartition: bool = False,
    ) -> FederatedExperiment:
        """Run a complete federated training experiment.

        Creates the experiment, runs Flower simulation, persists per-round
        metrics, and marks the experiment as completed or failed.

        Args:
            name: Human-readable experiment name.
            config: Experiment configuration with hyperparameters.
            n_clients: Number of federated clients to simulate.
            n_rounds: Number of federated communication rounds.
            aggregation_strategy: Strategy for aggregating client updates.
            local_epochs: Training epochs per client per round.
            fraction_train: Fraction of clients selected for training.
            fraction_evaluate: Fraction of clients for evaluation.
            force_repartition: Force data re-partitioning even if cached.

        Returns:
            Completed FederatedExperiment with final metrics.

        Raises:
            Exception: Propagates any simulation errors after marking
                experiment as failed.
        """
        # Create experiment (PENDING state)
        experiment = await self._experiment_service.create_federated_experiment(
            name=name,
            config=config,
            n_clients=n_clients,
            n_rounds=n_rounds,
            aggregation_strategy=aggregation_strategy,
        )
        experiment_id = experiment.experiment_id

        logger.info(f"Created federated experiment: {experiment_id}")

        try:
            # Transition to RUNNING
            await self._experiment_service.start_experiment(experiment_id)
            logger.info(f"Started federated experiment: {experiment_id}")

            # Create simulation manager
            manager = FederatedSimulationManager(
                data_dir=self._data_dir,
                storage_dir=self._storage_dir / experiment_id,
                num_clients=n_clients,
                random_seed=config.random_seed,
            )

            # Run Flower simulation
            logger.info(
                f"Starting federated simulation: {n_rounds} rounds, "
                f"{n_clients} clients"
            )
            result = manager.run_simulation(
                num_rounds=n_rounds,
                n_factors=config.n_factors,
                learning_rate=config.learning_rate,
                regularization=config.regularization,
                local_epochs=local_epochs,
                fraction_train=fraction_train,
                fraction_evaluate=fraction_evaluate,
                enable_centralized_eval=True,
                force_repartition=force_repartition,
            )

            # Persist per-round metrics to database
            await self._persist_federated_metrics(experiment_id, result)

            # Complete experiment with final metrics
            experiment = await self._experiment_service.complete_experiment(
                experiment_id=experiment_id,
                final_rmse=result.final_rmse,
                final_mae=result.final_mae,
                training_time_seconds=result.training_time_seconds,
            )

            logger.info(
                f"Completed federated experiment {experiment_id}: "
                f"RMSE={result.final_rmse:.4f}, MAE={result.final_mae:.4f}, "
                f"Best Round={result.best_round}"
            )

            return experiment

        except Exception as e:
            logger.error(f"Federated experiment {experiment_id} failed: {e}")
            await self._experiment_service.fail_experiment(experiment_id)
            raise

    async def _persist_training_metrics(
        self,
        experiment_id: str,
        result: TrainingResult,
    ) -> None:
        """Persist per-epoch metrics from training to the database.

        Args:
            experiment_id: UUID of the experiment.
            result: Training result containing metrics history.
        """
        metrics_to_persist: list[PerformanceMetric] = []

        # Extract training losses
        training_losses = result.metrics_logger.get_training_losses()
        for epoch, loss in enumerate(training_losses):
            metrics_to_persist.append(
                PerformanceMetric(
                    name="loss",
                    value=loss,
                    experiment_id=experiment_id,
                    context="training",
                    round_number=epoch,
                )
            )

        # Extract validation RMSE
        validation_rmse = result.metrics_logger.get_validation_rmse()
        for epoch, rmse in enumerate(validation_rmse):
            metrics_to_persist.append(
                PerformanceMetric(
                    name="rmse",
                    value=rmse,
                    experiment_id=experiment_id,
                    context="validation",
                    round_number=epoch,
                )
            )

        # Extract validation MAE
        validation_mae = result.metrics_logger.get_validation_mae()
        for epoch, mae in enumerate(validation_mae):
            if mae is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="mae",
                        value=mae,
                        experiment_id=experiment_id,
                        context="validation",
                        round_number=epoch,
                    )
                )

        # Batch persist all metrics
        if metrics_to_persist:
            await self._metrics_service.add_metrics_batch(
                experiment_id=experiment_id,
                metrics=metrics_to_persist,
            )
            logger.debug(
                f"Persisted {len(metrics_to_persist)} metrics for experiment {experiment_id}"
            )

    async def _persist_federated_metrics(
        self,
        experiment_id: str,
        result: FederatedSimulationResult,
    ) -> None:
        """Persist per-round metrics from federated simulation to the database.

        Converts Flower simulation metrics into PerformanceMetric entities
        and persists them via MetricsService.

        Args:
            experiment_id: UUID of the experiment.
            result: Federated simulation result containing per-round metrics.
        """
        metrics_to_persist: list[PerformanceMetric] = []

        for round_data in result.metrics_by_round:
            round_num = round_data.get("round", 0)

            # Centralized test metrics (server-side evaluation)
            if round_data.get("test_rmse") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="rmse",
                        value=round_data["test_rmse"],
                        experiment_id=experiment_id,
                        context="centralized_test",
                        round_number=round_num,
                    )
                )

            if round_data.get("test_mae") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="mae",
                        value=round_data["test_mae"],
                        experiment_id=experiment_id,
                        context="centralized_test",
                        round_number=round_num,
                    )
                )

            if round_data.get("test_loss") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="loss",
                        value=round_data["test_loss"],
                        experiment_id=experiment_id,
                        context="centralized_test",
                        round_number=round_num,
                    )
                )

            # Client-side aggregated evaluation metrics
            if round_data.get("client_eval_rmse") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="rmse",
                        value=round_data["client_eval_rmse"],
                        experiment_id=experiment_id,
                        context="client_aggregated",
                        round_number=round_num,
                    )
                )

            if round_data.get("client_eval_mae") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="mae",
                        value=round_data["client_eval_mae"],
                        experiment_id=experiment_id,
                        context="client_aggregated",
                        round_number=round_num,
                    )
                )

            # Training loss
            if round_data.get("train_loss") is not None:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="loss",
                        value=round_data["train_loss"],
                        experiment_id=experiment_id,
                        context="training",
                        round_number=round_num,
                    )
                )

        # Batch persist all metrics
        if metrics_to_persist:
            await self._metrics_service.add_metrics_batch(
                experiment_id=experiment_id,
                metrics=metrics_to_persist,
            )
            logger.info(
                f"Persisted {len(metrics_to_persist)} federated metrics "
                f"for experiment {experiment_id}"
            )

    async def evaluate_experiment(
        self,
        experiment_id: str,
        accelerator: str = "auto",
    ) -> dict[str, float]:
        """Evaluate a completed experiment on test data.

        Args:
            experiment_id: UUID of the experiment to evaluate.
            accelerator: Device accelerator.

        Returns:
            Dictionary with test metrics (rmse, mae).

        Raises:
            NotImplementedError: Test evaluation requires model persistence
                which is not yet implemented.
        """
        raise NotImplementedError(
            "Test evaluation requires loading a persisted model. "
            "Use trainer.evaluate() directly after training."
        )

    @property
    def data_metadata(self) -> Optional[dict]:
        """Return dataset metadata if data is loaded."""
        if self._data_loader is None:
            return None
        metadata = self._data_loader.get_metadata()
        return {
            "n_users": metadata.n_users,
            "n_items": metadata.n_items,
            "global_mean": metadata.global_mean,
            "train_size": metadata.train_size,
            "val_size": metadata.val_size,
            "test_size": metadata.test_size,
            "sparsity": metadata.sparsity,
        }
