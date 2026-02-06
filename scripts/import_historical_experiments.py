"""Import historical experiment results into the database.

This script reads experiment results from JSON files and CSV summary,
then creates Experiment and Metrics records in the database.
"""

import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment, FederatedExperiment
from app.core.metrics import ExperimentMetrics, PerformanceMetric
from app.infrastructure.database import get_session_factory
from app.infrastructure.repositories.experiment_repository import ExperimentRepository
from app.infrastructure.repositories.metrics_repository import MetricsRepository
from app.utils.types import AggregationStrategy


async def load_experiment_data(results_dir: Path) -> List[Dict]:
    """Load all experiment data from summary CSV."""
    summary_path = results_dir / "summary.csv"
    experiments = []

    with open(summary_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            experiments.append(row)

    print(f"Loaded {len(experiments)} experiments from summary.csv")
    return experiments


def load_metrics_json(results_dir: Path, experiment_type: str, seed: int) -> Dict:
    """Load metrics.json for a specific experiment."""
    metrics_path = results_dir / experiment_type / f"seed_{seed}" / "metrics.json"

    with open(metrics_path, "r") as f:
        return json.load(f)


def create_centralized_experiment(
    row: Dict,
    metrics_json: Dict,
) -> CentralizedExperiment:
    """Create a CentralizedExperiment from CSV row and JSON metrics."""
    config = Configuration(
        n_factors=int(row["n_factors"]),
        learning_rate=float(row["lr"]),
        regularization=float(row["weight_decay"]),
        n_epochs=int(row["epochs_trained"]),
        batch_size=int(row["batch_size"]),
        random_seed=int(row["seed"]),
    )

    # Create experiment
    experiment = CentralizedExperiment(
        experiment_id=str(uuid4()),
        name=f"Historical Centralized - Seed {row['seed']} ({row['client_group']})",
        config=config,
    )

    # Add per-epoch metrics from history
    validation_history = metrics_json.get("history", {}).get("validation", {})
    for epoch_str, values in validation_history.items():
        epoch = int(epoch_str)

        # Add RMSE metric
        experiment.add_epoch_metric(
            PerformanceMetric(
                name="val_rmse",
                value=values["rmse"],
                experiment_id=experiment.experiment_id,
                context=f"epoch_{epoch}",
                round_number=epoch,
            )
        )

        # Add MAE metric
        experiment.add_epoch_metric(
            PerformanceMetric(
                name="val_mae",
                value=values["mae"],
                experiment_id=experiment.experiment_id,
                context=f"epoch_{epoch}",
                round_number=epoch,
            )
        )

    # Add training loss metrics
    training_history = metrics_json.get("history", {}).get("training", {})
    for epoch_str, values in training_history.items():
        epoch = int(epoch_str)

        experiment.add_epoch_metric(
            PerformanceMetric(
                name="train_loss",
                value=values["loss"],
                experiment_id=experiment.experiment_id,
                context=f"epoch_{epoch}",
                round_number=epoch,
            )
        )

    # Create final metrics
    final_metrics = ExperimentMetrics(
        rmse=float(row["test_rmse"]),
        mae=float(row["test_mae"]),
        training_time_seconds=float(row["duration_seconds"]),
    )

    # Mark as completed with metrics
    experiment.mark_running()
    experiment.mark_completed(final_metrics)

    # Override timestamps with historical data
    experiment.created_at = datetime.fromisoformat(metrics_json["timestamp"])
    experiment.completed_at = datetime.fromisoformat(metrics_json["timestamp"])

    return experiment


def create_federated_experiment(
    row: Dict,
    metrics_json: Dict,
) -> FederatedExperiment:
    """Create a FederatedExperiment from CSV row and JSON metrics."""
    num_clients = int(float(row["num_clients"]))
    num_rounds = int(float(row["num_rounds"]))

    config = Configuration(
        n_factors=int(row["n_factors"]),
        learning_rate=float(row["lr"]),
        regularization=float(row["weight_decay"]),
        n_epochs=int(float(row["equivalent_epochs"])),
        batch_size=int(row["batch_size"]),
        random_seed=int(row["seed"]),
        n_clients=num_clients,
        n_rounds=num_rounds,
        aggregation_strategy=AggregationStrategy.FEDAVG,
    )

    # Create experiment
    experiment = FederatedExperiment(
        experiment_id=str(uuid4()),
        name=f"Historical Federated - Seed {row['seed']} ({row['client_group']})",
        config=config,
        n_clients=num_clients,
        n_rounds=num_rounds,
        aggregation_strategy=AggregationStrategy.FEDAVG,
    )

    # Add per-round metrics from centralized evaluation
    centralized_eval = metrics_json.get("history", {}).get("centralized_eval", {})
    for round_str, values in centralized_eval.items():
        round_num = int(round_str)

        # Add test RMSE metric
        experiment.round_metrics.append(
            PerformanceMetric(
                name="test_rmse",
                value=values["test_rmse"],
                experiment_id=experiment.experiment_id,
                context=f"round_{round_num}",
                round_number=round_num,
            )
        )

        # Add test MAE metric
        experiment.round_metrics.append(
            PerformanceMetric(
                name="test_mae",
                value=values["test_mae"],
                experiment_id=experiment.experiment_id,
                context=f"round_{round_num}",
                round_number=round_num,
            )
        )

        # Add test loss metric
        experiment.round_metrics.append(
            PerformanceMetric(
                name="test_loss",
                value=values["test_loss"],
                experiment_id=experiment.experiment_id,
                context=f"round_{round_num}",
                round_number=round_num,
            )
        )

    # Add training loss metrics
    train_history = metrics_json.get("history", {}).get("train", {})
    for round_str, values in train_history.items():
        round_num = int(round_str)

        experiment.round_metrics.append(
            PerformanceMetric(
                name="train_loss",
                value=values["agg_loss"],
                experiment_id=experiment.experiment_id,
                context=f"round_{round_num}",
                round_number=round_num,
            )
        )

    # Create final metrics
    final_metrics = ExperimentMetrics(
        rmse=float(row["test_rmse"]),
        mae=float(row["test_mae"]),
        training_time_seconds=float(row["duration_seconds"]),
    )

    # Mark as completed with metrics
    experiment.mark_running()
    experiment.mark_completed(final_metrics)

    # Override timestamps with historical data
    experiment.created_at = datetime.fromisoformat(metrics_json["timestamp"])
    experiment.completed_at = datetime.fromisoformat(metrics_json["timestamp"])

    return experiment


def extract_metrics_for_db(experiment) -> List[PerformanceMetric]:
    """Extract metrics for database insertion."""
    # Get the appropriate metrics list based on experiment type
    if hasattr(experiment, 'epoch_metrics'):
        return experiment.epoch_metrics
    else:  # FederatedExperiment
        return experiment.round_metrics


async def import_experiments():
    """Main import function."""
    results_dir = Path("project-notes/06-scratchpad/results")

    # Load all experiment data
    experiments_data = await load_experiment_data(results_dir)

    # Initialize database session and repositories
    session_factory = get_session_factory()
    async with session_factory() as session:
        experiment_repo = ExperimentRepository(session)
        metrics_repo = MetricsRepository(session)

        imported_count = 0

        for row in experiments_data:
            experiment_type = row["experiment"]
            seed = int(row["seed"])

            print(f"\nImporting {experiment_type} experiment (seed={seed})...")

            # Load detailed metrics
            metrics_json = load_metrics_json(results_dir, experiment_type, seed)

            # Create experiment entity
            if experiment_type == "centralized":
                experiment = create_centralized_experiment(row, metrics_json)
            else:  # federated
                experiment = create_federated_experiment(row, metrics_json)

            # Save experiment to database
            saved_experiment = await experiment_repo.add(experiment)
            print(f"  [OK] Saved experiment: {saved_experiment.name}")

            # Extract and save metrics in batch
            metrics_list = extract_metrics_for_db(experiment)
            if metrics_list:
                await metrics_repo.add_batch(metrics_list)
                print(f"  [OK] Saved {len(metrics_list)} metric records")

            imported_count += 1

        # Commit all changes
        await session.commit()
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Imported {imported_count} experiments!")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(import_experiments())
