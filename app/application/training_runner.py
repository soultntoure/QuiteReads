"""Background training runner.

Provides async functions to run training experiments in the background,
independent of the API request lifecycle.
"""

import asyncio
import logging
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Optional

from app.application.services import ExperimentService, MetricsService
from app.application import training_status
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.infrastructure.database import get_session_factory
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository

logger = logging.getLogger(__name__)

# Default paths (relative to project root)
DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"
DEFAULT_CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"
DEFAULT_STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "federated"


@dataclass
class TrainingContext:
    """Context containing services and paths for training."""

    experiment_service: ExperimentService
    metrics_service: MetricsService
    data_dir: Path
    checkpoint_dir: Path
    storage_dir: Path


async def run_experiment_training(
    experiment_id: str,
    data_dir: Optional[Path] = None,
    checkpoint_dir: Optional[Path] = None,
) -> None:
    """Run training for an experiment in the background.

    Creates its own database session since this runs independently
    of the original API request.

    Args:
        experiment_id: UUID of the experiment to train.
        data_dir: Path to data directory. Defaults to project's data/.
        checkpoint_dir: Path for model checkpoints. Defaults to checkpoints/.
    """
    data_dir = data_dir or DEFAULT_DATA_DIR
    checkpoint_dir = checkpoint_dir or DEFAULT_CHECKPOINT_DIR
    storage_dir = DEFAULT_STORAGE_DIR

    logger.info(f"Starting background training for experiment {experiment_id}")

    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # Create repositories and services with fresh session
            experiment_repo = ExperimentRepository(session)
            metrics_repo = MetricsRepository(session)

            experiment_service = ExperimentService(experiment_repo, metrics_repo)
            metrics_service = MetricsService(metrics_repo, experiment_repo)

            # Create training context
            ctx = TrainingContext(
                experiment_service=experiment_service,
                metrics_service=metrics_service,
                data_dir=data_dir,
                checkpoint_dir=checkpoint_dir,
                storage_dir=storage_dir,
            )

            # Retrieve experiment to determine type
            experiment = await experiment_service.get_experiment_by_id(experiment_id)

            # Run appropriate training based on experiment type
            if isinstance(experiment, CentralizedExperiment):
                # Start training status tracking
                training_status.start_training(
                    experiment_id=experiment_id,
                    experiment_type="centralized",
                    total_epochs=experiment.config.n_epochs,
                )
                await _run_centralized_training(ctx, experiment)
            elif isinstance(experiment, FederatedExperiment):
                # Start training status tracking
                training_status.start_training(
                    experiment_id=experiment_id,
                    experiment_type="federated",
                    total_rounds=experiment.n_rounds,
                )
                await _run_federated_training(ctx, experiment)
            else:
                logger.error(f"Unknown experiment type: {type(experiment)}")
                await experiment_service.fail_experiment(experiment_id)

            await session.commit()
            logger.info(f"Background training completed for experiment {experiment_id}")

        except Exception as e:
            logger.error(f"Background training failed for {experiment_id}: {e}")
            training_status.fail_training(str(e))
            await session.rollback()

            # Try to mark experiment as failed in a new session
            await _mark_experiment_failed(experiment_id)
            raise


async def _run_centralized_training(
    ctx: TrainingContext,
    experiment: CentralizedExperiment,
) -> None:
    """Execute centralized training for an existing experiment."""
    from app.application.data.dataset_loader import DatasetLoader
    from app.application.training.centralized_trainer import CentralizedTrainer
    from app.core.metrics import PerformanceMetric

    logger.info(f"Running centralized training for {experiment.experiment_id}")

    # Load data
    training_status.update_step("loading_data")
    data_loader = DatasetLoader(ctx.data_dir)
    data_loader.load()

    batch_size = experiment.config.batch_size or 1024
    train_loader = data_loader.get_train_loader(batch_size=batch_size)
    val_loader = data_loader.get_val_loader(batch_size=batch_size)

    # Create and run trainer
    training_status.update_step("initializing")
    trainer = CentralizedTrainer(
        config=experiment.config,
        n_users=data_loader.n_users,
        n_items=data_loader.n_items,
        global_mean=data_loader.global_mean,
        checkpoint_dir=ctx.checkpoint_dir,
    )

    # Define progress callback for live updates
    loop = asyncio.get_event_loop()

    def report_progress(epoch: int, metrics: dict[str, float]) -> None:
        """Update training status and persist metrics at end of epoch."""
        # Update status (in-memory, thread-safe enough for this use case)
        next_epoch = min(epoch + 2, experiment.config.n_epochs)
        training_status.update_step("training", current_epoch=next_epoch)

        # Schedule metric persistence on the main event loop
        async def _persist_metrics():
            metrics_to_persist: list[PerformanceMetric] = []
            
            # Map Lightning metrics to PerformanceMetric
            if "train_loss" in metrics:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="loss",
                        value=metrics["train_loss"],
                        experiment_id=experiment.experiment_id,
                        context="training",
                        round_number=epoch,
                    )
                )
            
            if "val_rmse" in metrics:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="rmse",
                        value=metrics["val_rmse"],
                        experiment_id=experiment.experiment_id,
                        context="validation",
                        round_number=epoch,
                    )
                )

            if "val_mae" in metrics:
                metrics_to_persist.append(
                    PerformanceMetric(
                        name="mae",
                        value=metrics["val_mae"],
                        experiment_id=experiment.experiment_id,
                        context="validation",
                        round_number=epoch,
                    )
                )
            
            if metrics_to_persist:
                await ctx.metrics_service.add_metrics_batch(
                    experiment_id=experiment.experiment_id,
                    metrics=metrics_to_persist,
                )

        # Schedule the coroutine
        asyncio.run_coroutine_threadsafe(_persist_metrics(), loop)

    # Training with epoch progress callback
    training_status.update_step("training", current_epoch=1)
    
    # Run training in executor to avoid blocking the event loop
    def run_training_sync():
        return trainer.train(
            train_loader, 
            val_loader, 
            accelerator="auto",
            on_epoch_end=report_progress
        )

    result = await loop.run_in_executor(None, run_training_sync)
    
    training_status.update_step("validating")

    # Metrics are already persisted live, but we ensure the final result is consistent.
    # We can skip re-persisting all metrics at the end, or just persist the final result.
    # The original implementation persisted history here. 
    # Since we persist live, we might duplicate it if we run the code below?
    # Actually, MetricsService.add_metrics_batch just adds rows. Duplicates might be an issue depending on DB constraints.
    # Assuming the DB allows multiple metrics for same epoch (it shouldn't, but let's be safe).
    # Since we persist LIVE, we don't need to bulk persist at the end.
    # However, let's keep the persistence at the end just in case live update missed something/failed?
    # No, duplicates are bad. Let's remove the block that persists all metrics at the end.
    # The final completion call handles saving final_rmse/mae as experiment attributes.

    training_status.update_step("saving")
    
    # Complete experiment
    await ctx.experiment_service.complete_experiment(
        experiment_id=experiment.experiment_id,
        final_rmse=result.final_rmse,
        final_mae=result.final_mae,
        training_time_seconds=result.training_time_seconds,
    )
    
    training_status.complete_training()


async def _run_federated_training(
    ctx: TrainingContext,
    experiment: FederatedExperiment,
) -> None:
    """Execute federated training for an existing experiment."""
    from app.application.training.federated_simulation_manager import (
        FederatedSimulationManager,
    )
    from app.core.metrics import PerformanceMetric

    logger.info(f"Running federated training for {experiment.experiment_id}")

    training_status.update_step("loading_data")
    storage_dir = ctx.storage_dir / experiment.experiment_id

    # Create simulation manager
    training_status.update_step("initializing")
    sim_manager = FederatedSimulationManager(
        data_dir=ctx.data_dir,
        storage_dir=storage_dir,
        num_clients=experiment.n_clients,
        random_seed=experiment.config.random_seed,
    )

    batch_size = experiment.config.batch_size or 1024
    local_epochs = experiment.config.n_epochs or 5

    # Build partial function for simulation
    def run_sync():
        return sim_manager.run_simulation(
            num_rounds=experiment.n_rounds,
            n_factors=experiment.config.n_factors,
            learning_rate=experiment.config.learning_rate,
            regularization=experiment.config.regularization,
            local_epochs=local_epochs,
            batch_size=batch_size,
            fraction_train=1.0,
            fraction_evaluate=1.0,
            enable_centralized_eval=True,
            force_repartition=False,
        )

    # Run simulation in executor thread to avoid blocking the event loop
    # This allows the API to respond to status polling requests
    training_status.update_step("training", current_round=1)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_sync)
    
    training_status.update_step("aggregating")

    # Persist per-round metrics
    metrics_to_persist: list[PerformanceMetric] = []

    for round_data in result.metrics_by_round:
        round_num = round_data.get("round", 0)

        if round_data.get("test_rmse") is not None:
            metrics_to_persist.append(
                PerformanceMetric(
                    name="rmse",
                    value=round_data["test_rmse"],
                    experiment_id=experiment.experiment_id,
                    context="centralized_test",
                    round_number=round_num,
                )
            )

        if round_data.get("test_mae") is not None:
            metrics_to_persist.append(
                PerformanceMetric(
                    name="mae",
                    value=round_data["test_mae"],
                    experiment_id=experiment.experiment_id,
                    context="centralized_test",
                    round_number=round_num,
                )
            )

        if round_data.get("test_loss") is not None:
            metrics_to_persist.append(
                PerformanceMetric(
                    name="loss",
                    value=round_data["test_loss"],
                    experiment_id=experiment.experiment_id,
                    context="centralized_test",
                    round_number=round_num,
                )
            )

        if round_data.get("train_loss") is not None:
            metrics_to_persist.append(
                PerformanceMetric(
                    name="loss",
                    value=round_data["train_loss"],
                    experiment_id=experiment.experiment_id,
                    context="training",
                    round_number=round_num,
                )
            )

    training_status.update_step("saving")
    if metrics_to_persist:
        await ctx.metrics_service.add_metrics_batch(
            experiment_id=experiment.experiment_id,
            metrics=metrics_to_persist,
        )

    # Complete experiment
    await ctx.experiment_service.complete_experiment(
        experiment_id=experiment.experiment_id,
        final_rmse=result.final_rmse,
        final_mae=result.final_mae,
        training_time_seconds=result.training_time_seconds,
    )
    
    training_status.complete_training()


async def _mark_experiment_failed(experiment_id: str) -> None:
    """Mark an experiment as failed in a new database session.

    Used for error recovery when the main session has issues.
    """
    session_factory = get_session_factory()

    try:
        async with session_factory() as session:
            experiment_repo = ExperimentRepository(session)
            metrics_repo = MetricsRepository(session)
            service = ExperimentService(experiment_repo, metrics_repo)

            try:
                await service.fail_experiment(experiment_id)
                await session.commit()
            except Exception:
                # Experiment might not be in RUNNING state, ignore
                pass
    except Exception as e:
        logger.error(f"Failed to mark experiment {experiment_id} as failed: {e}")
