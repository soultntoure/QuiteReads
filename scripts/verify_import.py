"""Verify that experiments were imported correctly."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database import get_session_factory
from app.infrastructure.repositories.experiment_repository import ExperimentRepository
from app.infrastructure.repositories.metrics_repository import MetricsRepository


async def verify_import():
    """Verify imported data."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        experiment_repo = ExperimentRepository(session)
        metrics_repo = MetricsRepository(session)

        # Get all experiments
        experiments = await experiment_repo.get_all()

        print(f"\n{'='*70}")
        print(f"Total Experiments: {len(experiments)}")
        print(f"{'='*70}\n")

        centralized_count = 0
        federated_count = 0

        for exp in experiments:
            exp_type = exp.experiment_type
            if exp_type == "centralized":
                centralized_count += 1
            else:
                federated_count += 1

            # Get metrics for this experiment
            metrics = await metrics_repo.get_by_experiment(exp.experiment_id)

            print(f"[{exp_type.upper()}] {exp.name}")
            print(f"  ID: {exp.experiment_id}")
            print(f"  Status: {exp.status.value}")
            print(f"  Created: {exp.created_at}")
            if exp.metrics:
                print(f"  Final RMSE: {exp.metrics.rmse:.4f}")
                print(f"  Final MAE: {exp.metrics.mae:.4f}")
                print(f"  Training Time: {exp.metrics.training_time_seconds:.2f}s")
            print(f"  Metric Records: {len(metrics)}")
            print()

        print(f"{'='*70}")
        print(f"Centralized Experiments: {centralized_count}")
        print(f"Federated Experiments: {federated_count}")
        print(f"{'='*70}\n")

        # Show sample metrics for first experiment
        if experiments:
            first_exp = experiments[0]
            metrics = await metrics_repo.get_by_experiment(first_exp.experiment_id)

            print(f"\nSample Metrics for: {first_exp.name}")
            print(f"{'='*70}")
            for metric in metrics[:5]:  # Show first 5
                print(f"  {metric.name} @ round {metric.round_number}: {metric.value:.4f}")
            if len(metrics) > 5:
                print(f"  ... and {len(metrics) - 5} more metrics")


if __name__ == "__main__":
    asyncio.run(verify_import())
