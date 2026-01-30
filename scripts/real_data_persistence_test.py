"""Real data persistence test: train centralized model with actual Goodreads data.

Trains a centralized matrix factorization model for 3 epochs using real data
from data/splits/ and persists to PostgreSQL. Used for manual verification
of end-to-end persistence.

Usage:
    uv run python scripts/real_data_persistence_test.py

After running, verify persistence with docker exec commands provided in output.
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.data.dataset_loader import DatasetLoader
from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.infrastructure.database import get_engine, get_session_factory
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository


async def main():
    """Run centralized experiment with real Goodreads data."""
    # Get database session
    engine = get_engine()
    session_factory = get_session_factory()

    data_dir = Path("data")

    # Verify data exists
    loader = DatasetLoader(data_dir)
    try:
        loader.verify_data_exists()
        print("✓ Data files verified")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nPlease ensure data preprocessing has been run.")
        sys.exit(1)

    async with session_factory() as session:
        # Wire up repositories and services
        experiment_repo = ExperimentRepository(session)
        metrics_repo = MetricsRepository(session)
        experiment_service = ExperimentService(experiment_repo, metrics_repo)
        metrics_service = MetricsService(metrics_repo, experiment_repo)

        # Create experiment manager
        manager = ExperimentManager(
            experiment_service=experiment_service,
            metrics_service=metrics_service,
            data_dir=data_dir,
            batch_size=1024,
        )

        # Configure experiment (3 epochs as requested)
        config = Configuration(
            n_factors=16,
            n_epochs=3,
            learning_rate=0.01,
            regularization=0.01,
        )

        print("\n" + "="*70)
        print("Starting Centralized Experiment with Real Data")
        print("="*70)
        print(f"Data directory: {data_dir.absolute()}")
        print(f"Config: {config}")
        print()

        # Run experiment
        result = await manager.run_centralized_experiment(
            name="Real Data Persistence Test",
            config=config,
            accelerator="cpu",
        )

        # Commit to ensure data is visible in database
        await session.commit()

        print("\n" + "="*70)
        print("Experiment Completed")
        print("="*70)
        print(f"Experiment ID: {result.experiment_id}")
        print(f"Status: {result.status}")
        print(f"Final RMSE: {result.get_final_rmse():.4f}")
        print(f"Final MAE: {result.get_final_mae():.4f}")
        print()

        # Retrieve and display persisted metrics
        metrics = await metrics_repo.get_by_experiment(result.experiment_id)
        print(f"Persisted {len(metrics)} metrics to PostgreSQL")
        print("\nMetrics by epoch:")
        for epoch in range(1, config.n_epochs + 1):
            epoch_metrics = [m for m in metrics if m.round_number == epoch]
            if epoch_metrics:
                print(f"\n  Epoch {epoch}:")
                for m in sorted(epoch_metrics, key=lambda x: x.name):
                    print(f"    {m.name:>5s} = {m.value:.4f}  ({m.context})")

        print("\n" + "="*70)
        print("Database Verification Commands")
        print("="*70)
        print("\nUse these docker exec commands to manually verify persistence:\n")

        print("# 1. View all experiments:")
        print(f'docker exec -it fedrec-db psql -U postgres -d fedrec -c "SELECT id, name, experiment_type, status, created_at FROM experiments ORDER BY created_at DESC LIMIT 5;"')
        print()

        print("# 2. View this specific experiment:")
        print(f'docker exec -it fedrec-db psql -U postgres -d fedrec -c "SELECT id, name, experiment_type, status, config, final_rmse, final_mae, training_time_seconds FROM experiments WHERE id=\'{result.experiment_id}\';"')
        print()

        print("# 3. View metrics for this experiment:")
        print(f'docker exec -it fedrec-db psql -U postgres -d fedrec -c "SELECT id, round_number, name, value, context, recorded_at FROM metrics WHERE experiment_id=\'{result.experiment_id}\' ORDER BY round_number, name;"')
        print()

        print("# 4. Count metrics per epoch:")
        print(f'docker exec -it fedrec-db psql -U postgres -d fedrec -c "SELECT round_number, COUNT(*) as metric_count FROM metrics WHERE experiment_id=\'{result.experiment_id}\' GROUP BY round_number ORDER BY round_number;"')
        print()

        print("# 5. View config JSON formatted:")
        print(f'docker exec -it fedrec-db psql -U postgres -d fedrec -c "SELECT jsonb_pretty(config::jsonb) FROM experiments WHERE id=\'{result.experiment_id}\';"')
        print()

        print("SUCCESS: Real data experiment persisted to PostgreSQL.")
        print("="*70 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
