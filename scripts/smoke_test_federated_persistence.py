"""Smoke test: run a federated experiment against real PostgreSQL.

Verifies metrics and experiments are persisted end-to-end for federated learning.
Uses synthetic data so no dataset files are needed.

Usage:
    uv run python scripts/smoke_test_federated_persistence.py
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from torch.utils.data import DataLoader, TensorDataset

from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.infrastructure.database import get_engine, get_session_factory
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.types import AggregationStrategy


def create_synthetic_federated_data(tmp_dir: Path, n_clients: int = 5) -> Path:
    """Create synthetic partitioned data for federated simulation.
    
    Creates the same structure that UserPartitioner would produce:
    - data_dir: Contains train.parquet-like metadata
    - partition_dir: Contains per-client data files
    
    Returns:
        Path to the data directory.
    """
    n_samples_per_client = 100
    n_users = 50
    n_items = 30
    
    data_dir = tmp_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    partition_dir = tmp_dir / "partitions"
    partition_dir.mkdir(parents=True, exist_ok=True)
    
    # Create partition config file (to signal partitions exist)
    partition_config = {
        "num_clients": n_clients,
        "strategy": "user_based",
        "seed": 42,
    }
    (partition_dir / "partition_config.json").write_text(json.dumps(partition_config))
    
    # Create per-client data files
    for client_id in range(n_clients):
        client_dir = partition_dir / f"client_{client_id}"
        client_dir.mkdir(exist_ok=True)
        
        # Generate client-specific data
        user_ids = torch.randint(0, n_users, (n_samples_per_client,))
        item_ids = torch.randint(0, n_items, (n_samples_per_client,))
        ratings = torch.rand(n_samples_per_client) * 4 + 1
        
        # Save as tensors (simulating what partitioner saves)
        torch.save({
            "user_ids": user_ids,
            "item_ids": item_ids,
            "ratings": ratings,
        }, client_dir / "train.pt")
        
        # Create validation split (smaller)
        val_size = n_samples_per_client // 5
        torch.save({
            "user_ids": user_ids[:val_size],
            "item_ids": item_ids[:val_size],
            "ratings": ratings[:val_size],
        }, client_dir / "val.pt")
    
    # Create metadata file
    metadata = {
        "n_users": n_users,
        "n_items": n_items,
        "global_mean": 3.0,
        "n_train": n_samples_per_client * n_clients,
        "n_val": (n_samples_per_client // 5) * n_clients,
        "n_test": 200,
    }
    (data_dir / "metadata.json").write_text(json.dumps(metadata))
    
    # Create test set tensors for centralized evaluation
    test_users = torch.randint(0, n_users, (200,))
    test_items = torch.randint(0, n_items, (200,))
    test_ratings = torch.rand(200) * 4 + 1
    
    torch.save({
        "user_ids": test_users,
        "item_ids": test_items,
        "ratings": test_ratings,
    }, data_dir / "test.pt")
    
    return data_dir, partition_dir, metadata


def create_mock_simulation_result(n_rounds: int):
    """Create a mock FederatedSimulationResult for testing persistence."""
    from app.application.training.federated_simulation_manager import (
        FederatedSimulationResult,
    )
    
    # Generate decreasing RMSE to simulate learning
    metrics_by_round = []
    for round_num in range(1, n_rounds + 1):
        # RMSE starts at ~1.5 and decreases
        rmse = 1.5 - (0.08 * round_num) + (torch.rand(1).item() * 0.05)
        mae = rmse * 0.7  # MAE is typically ~70% of RMSE
        
        metrics_by_round.append({
            "round": round_num,
            "test_rmse": rmse,
            "test_mae": mae,
            "client_eval_rmse": rmse + 0.05,
            "client_eval_mae": mae + 0.03,
            "train_loss": 0.5 - (0.03 * round_num),
        })
    
    # Final round metrics
    final_rmse = metrics_by_round[-1]["test_rmse"]
    final_mae = metrics_by_round[-1]["test_mae"]
    
    # Find best round
    best_round = min(range(len(metrics_by_round)), 
                     key=lambda i: metrics_by_round[i]["test_rmse"])
    best_rmse = metrics_by_round[best_round]["test_rmse"]
    best_mae = metrics_by_round[best_round]["test_mae"]
    
    return FederatedSimulationResult(
        final_rmse=final_rmse,
        final_mae=final_mae,
        best_rmse=best_rmse,
        best_mae=best_mae,
        best_round=best_round + 1,  # 1-indexed
        training_time_seconds=10.5,
        num_rounds=n_rounds,
        metrics_by_round=metrics_by_round,
        raw_result=None,
    )


async def main():
    """Run federated smoke test with real database and mocked simulation."""
    import tempfile
    
    # Get a real database session
    engine = get_engine()
    session_factory = get_session_factory()
    
    # Create temporary directory for synthetic data
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create synthetic federated data
        n_clients = 5
        n_rounds = 3
        data_dir, partition_dir, metadata = create_synthetic_federated_data(
            tmp_path, n_clients=n_clients
        )
        
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
                data_dir=data_dir,
                storage_dir=tmp_path / "storage",
                batch_size=64,
            )
            
            # Mock the FederatedSimulationManager to avoid actual Flower simulation
            mock_result = create_mock_simulation_result(n_rounds)
            
            with patch(
                "app.application.experiment_manager.FederatedSimulationManager"
            ) as MockManager:
                # Configure mock
                mock_instance = MagicMock()
                mock_instance.run_simulation.return_value = mock_result
                MockManager.return_value = mock_instance
                
                config = Configuration(
                    n_factors=8,
                    learning_rate=0.02,
                    regularization=0.005,
                )
                
                print(f"Running federated experiment ({n_rounds} rounds, {n_clients} clients)...")
                result = await manager.run_federated_experiment(
                    name="Federated Smoke Test",
                    config=config,
                    n_clients=n_clients,
                    n_rounds=n_rounds,
                    aggregation_strategy=AggregationStrategy.FEDAVG,
                    local_epochs=3,
                )
                
                print(f"\nExperiment ID: {result.experiment_id}")
                print(f"Status: {result.status}")
                print(f"Experiment Type: {result.experiment_type}")
                print(f"Final RMSE: {result.get_final_rmse():.4f}")
                print(f"Final MAE: {result.get_final_mae():.4f}")
                print(f"N Clients: {result.n_clients}")
                print(f"N Rounds: {result.n_rounds}")
                print(f"Aggregation Strategy: {result.aggregation_strategy}")
                
                # Commit so data is visible in psql
                await session.commit()
                
                # Query back metrics
                metrics = await metrics_repo.get_by_experiment(result.experiment_id)
                print(f"\nPersisted {len(metrics)} metrics to PostgreSQL:")
                
                # Group by round for display
                metrics_sorted = sorted(metrics, key=lambda x: (x.round_number, x.name))
                for m in metrics_sorted:
                    print(
                        f"  round={m.round_number}  {m.name:>15s} = {m.value:.4f}  "
                        f"({m.context})"
                    )
                
                # Verify expected metrics count
                # Expecting: test_rmse, test_mae, client_eval_rmse, client_eval_mae, 
                # train_loss per round = 5 metrics * n_rounds
                expected_metrics = n_rounds * 5  # 5 metrics per round
                if len(metrics) >= n_rounds * 2:  # At minimum: rmse + mae per round
                    print(
                        f"\n✓ SUCCESS: {len(metrics)} metrics persisted and "
                        "retrieved from PostgreSQL."
                    )
                else:
                    print(
                        f"\n✗ FAILURE: Expected at least {n_rounds * 2} metrics, "
                        f"got {len(metrics)}."
                    )
                    sys.exit(1)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
