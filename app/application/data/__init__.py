"""Data handling module.

Provides data loading, preprocessing, and partitioning for recommendation
experiments.
"""

from app.application.data.client_datamodule import ClientDataModule
from app.application.data.data_loader_factory import create_eval_loader, create_train_loader
from app.application.data.dataset_loader import DatasetLoader, DatasetMetadata
from app.application.data.partitioner import (
    PartitionConfig,
    PartitionResult,
    UserPartitioner,
    verify_partitions,
)
from app.application.data.preprocessing import (
    PreprocessingConfig,
    run_preprocessing_pipeline,
)
from app.application.data.ratings_dataset import RatingsDataset


def load_partition_config(partition_dir):
    """Load partition configuration from JSON file.

    Convenience wrapper around UserPartitioner.load_partition_config().

    Args:
        partition_dir: Directory containing partition_config.json

    Returns:
        Configuration dictionary with keys: num_clients, total_users,
        total_items, global_mean, etc.
    """
    return UserPartitioner.load_partition_config(partition_dir)


__all__ = [
    # Dataset and loaders
    "RatingsDataset",
    "DatasetLoader",
    "DatasetMetadata",
    # DataLoader factory
    "create_train_loader",
    "create_eval_loader",
    # Partitioning
    "UserPartitioner",
    "PartitionConfig",
    "PartitionResult",
    "verify_partitions",
    "load_partition_config",
    # Preprocessing
    "PreprocessingConfig",
    "run_preprocessing_pipeline",
    # Federated client data
    "ClientDataModule",
]
