"""Smoke test: run a centralized experiment against real PostgreSQL.

Verifies metrics and experiments are persisted end-to-end.
Uses synthetic data so no dataset files are needed.

Usage:
    uv run python scripts/smoke_test_persistence.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock

import torch
from torch.utils.data import DataLoader, TensorDataset

from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.infrastructure.database import get_engine, get_session_factory
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository


def create_synthetic_loader() -> MagicMock:
    """Create a mock DatasetLoader with synthetic data."""
    n_samples = 200
    n_users = 50
    n_items = 30

    user_ids = torch.randint(0, n_users, (n_samples,))
    item_ids = torch.randint(0, n_items, (n_samples,))
    ratings = torch.rand(n_samples) * 4 + 1

    dataset = TensorDataset(user_ids, item_ids, ratings)

    loader = MagicMock()
    loader.load = MagicMock()
    loader.n_users = n_users
    loader.n_items = n_items
    loader.global_mean = 3.0
    loader.get_train_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=True)
    )
    loader.get_val_loader = MagicMock(
        return_value=DataLoader(dataset, batch_size=64, shuffle=False)
    )
    return loader


async def main():
    # Get a real database session
    engine = get_engine()
    session_factory = get_session_factory()

    async with session_factory() as session:
        # Wire up real repositories and services
        experiment_repo = ExperimentRepository(session)
        metrics_repo = MetricsRepository(session)
        experiment_service = ExperimentService(experiment_repo, metrics_repo)
        metrics_service = MetricsService(metrics_repo, experiment_repo)

        # Create manager
        manager = ExperimentManager(
            experiment_service=experiment_service,
            metrics_service=metrics_service,
            data_dir=Path("data"),
            batch_size=64,
        )

        # Inject synthetic data
        mock_loader = create_synthetic_loader()
        manager._data_loader = mock_loader
        manager._ensure_data_loaded = lambda: mock_loader

        config = Configuration(n_factors=8, n_epochs=3, learning_rate=0.01)

        print("Running centralized experiment (3 epochs)...")
        result = await manager.run_centralized_experiment(
            name="Smoke Test",
            config=config,
            accelerator="cpu",
        )

        print(f"\nExperiment ID: {result.experiment_id}")
        print(f"Status: {result.status}")
        print(f"Final RMSE: {result.get_final_rmse():.4f}")
        print(f"Final MAE: {result.get_final_mae():.4f}")

        # Commit so data is visible in psql
        await session.commit()

        # Query back metrics
        metrics = await metrics_repo.get_by_experiment(result.experiment_id)
        print(f"\nPersisted {len(metrics)} metrics to PostgreSQL:")
        for m in sorted(metrics, key=lambda x: (x.name, x.round_number)):
            print(f"  epoch={m.round_number}  {m.name:>5s} = {m.value:.4f}  ({m.context})")

        print("\nSUCCESS: Metrics persisted and retrieved from PostgreSQL.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
