"""Data handling module.

Provides data loading, preprocessing, and partitioning for recommendation
experiments.
"""

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
    # Preprocessing
    "PreprocessingConfig",
    "run_preprocessing_pipeline",
]
