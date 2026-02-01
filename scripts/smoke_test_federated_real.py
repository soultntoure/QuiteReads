"""Smoke test: run a REAL federated experiment against PostgreSQL.

This is an end-to-end integration test that:
- Uses real Flower simulation (flwr.simulation.run_simulation)
- Uses real PyTorch Lightning training on clients
- Uses real partitioned data from data/federated
- Persists metrics to real PostgreSQL

Requires:
- PostgreSQL running (docker compose up -d)
- Partitioned data in data/federated (run scripts/partition_data.py if missing)

Usage:
    uv run python scripts/smoke_test_federated_real.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.experiment_manager import ExperimentManager
from app.application.services.experiment_service import ExperimentService
from app.application.services.metrics_service import MetricsService
from app.core.configuration import Configuration
from app.infrastructure.database import get_engine, get_session_factory
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.utils.types import AggregationStrategy


async def main():
    """Run real federated experiment with actual Flower simulation."""
    # Paths
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data" / "splits"  # For DatasetLoader (train/val/test)
    partition_dir = project_root / "data" / "federated"  # Pre-partitioned client data
    
    # Verify data exists
    if not partition_dir.exists():
        print(f"ERROR: Partition directory not found: {partition_dir}")
        print("Run: uv run python scripts/partition_data.py")
        sys.exit(1)
    
    partition_config = partition_dir / "partition_config.json"
    if not partition_config.exists():
        print(f"ERROR: partition_config.json not found in {partition_dir}")
        sys.exit(1)
    
    # Read partition config to get number of clients
    import json
    with open(partition_config) as f:
        config_data = json.load(f)
    n_clients = config_data["num_clients"]
    
    print("=" * 60)
    print("FEDERATED SMOKE TEST - REAL END-TO-END")
    print("=" * 60)
    print(f"Data directory: {data_dir}")
    print(f"Partition directory: {partition_dir}")
    print(f"Number of clients: {n_clients}")
    print(f"Total users: {config_data['total_users']}")
    print(f"Total items: {config_data['total_items']}")
    print(f"Global mean: {config_data['global_mean']:.4f}")
    print("=" * 60)
    
    # Get a real database session
    engine = get_engine()
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Wire up real repositories and services
        experiment_repo = ExperimentRepository(session)
        metrics_repo = MetricsRepository(session)
        experiment_service = ExperimentService(experiment_repo, metrics_repo)
        metrics_service = MetricsService(metrics_repo, experiment_repo)
        
        # Create manager with real paths
        # Note: ExperimentManager uses data_dir for DatasetLoader,
        # and storage_dir for FederatedSimulationManager partitions
        manager = ExperimentManager(
            experiment_service=experiment_service,
            metrics_service=metrics_service,
            data_dir=data_dir,  # For DatasetLoader
            storage_dir=project_root / "results" / "smoke_test_federated",
            batch_size=1024,
        )
        
        # Configuration for real training
        config = Configuration(
            n_factors=16,
            learning_rate=0.02,
            regularization=0.005,
        )
        
        # Run fewer rounds for smoke test
        n_rounds = 2  # Quick smoke test
        local_epochs = 2  # Faster training
        
        print(f"\nRunning REAL federated experiment:")
        print(f"  - {n_rounds} rounds")
        print(f"  - {n_clients} clients")
        print(f"  - {local_epochs} local epochs per client per round")
        print(f"  - {config.n_factors} latent factors")
        print("\nThis will run actual Flower simulation with PyTorch Lightning...")
        print()
        
        try:
            result = await manager.run_federated_experiment(
                name="Real Federated Smoke Test",
                config=config,
                n_clients=n_clients,
                n_rounds=n_rounds,
                aggregation_strategy=AggregationStrategy.FEDAVG,
                local_epochs=local_epochs,
                fraction_train=1.0,
                fraction_evaluate=1.0,
                force_repartition=False,  # Use existing partitions
            )
            
            print("\n" + "=" * 60)
            print("EXPERIMENT COMPLETED")
            print("=" * 60)
            print(f"Experiment ID: {result.experiment_id}")
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
            
            # Verify success
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
                
        except Exception as e:
            print(f"\n✗ EXPERIMENT FAILED: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    await engine.dispose()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
