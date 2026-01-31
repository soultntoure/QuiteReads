"""Partition Goodreads data for federated learning.

Runs the UserPartitioner to create client-specific data partitions
from the preprocessed train/val splits.

Usage:
    uv run python scripts/partition_data.py --num-clients 10
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.application.data.partitioner import (
    PartitionConfig,
    UserPartitioner,
    verify_partitions,
)


def main():
    print("Starting data partitioning for 2 clients...")

    parser = argparse.ArgumentParser(
        description="Partition Goodreads data for federated learning"
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=2,
        help="Number of federated clients (default: 2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing splits/ folder (default: data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/federated"),
        help="Output directory for partitioned data (default: data/federated)",
    )

    args = parser.parse_args()

    print(f"=== Federated Data Partitioning ===")
    print(f"Number of clients: {args.num_clients}")
    print(f"Random seed: {args.seed}")
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print()

    # Create partitioner
    config = PartitionConfig(num_clients=args.num_clients, seed=args.seed)
    partitioner = UserPartitioner(config)

    # Run partitioning
    print("Partitioning data...")
    result = partitioner.partition(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
    )

    print(f"\n✓ Partitioning complete!")
    print(f"\nPartition Statistics:")
    print(f"  Clients: {result.num_clients}")
    print(f"  Total users: {result.global_n_users}")
    print(f"  Total items: {result.global_n_items}")
    print(f"  Global mean rating: {result.global_mean:.3f}")
    print(f"\nData Distribution:")
    for client_id in range(result.num_clients):
        train_count, val_count = result.interactions_per_client[client_id]
        user_count = result.users_per_client[client_id]
        print(
            f"  Client {client_id}: {user_count} users, "
            f"{train_count} train interactions, {val_count} val interactions"
        )

    print(f"\nOutput:")
    print(f"  Partitioned data: {result.output_dir}")
    print(f"  Configuration: {result.config_path}")

    # Verify partitions
    print(f"\nVerifying partitions...")
    verify_partitions(result.output_dir)
    print("✓ Partitions verified (disjoint and complete)")


if __name__ == "__main__":
    main()
