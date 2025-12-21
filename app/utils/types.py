"""Type definitions.

Shared Enums and type aliases used throughout the application.
"""

from enum import Enum


class ExperimentStatus(Enum):
    """Status of an experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AggregationStrategy(Enum):
    """Federated learning aggregation strategies."""

    FEDAVG = "fedavg"
    # Add FEDPROX later if needed


class ModelType(Enum):
    """Supported recommender models."""

    BIASED_SVD = "biased_svd"
