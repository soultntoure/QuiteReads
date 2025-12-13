"""Experiment configuration models."""

from dataclasses import dataclass
from typing import Optional

from app.utils.types import AggregationStrategy, ModelType


@dataclass
class Configuration:
    """Experiment hyperparameters and settings."""

    model_type: ModelType = ModelType.BIASED_SVD
    n_factors: int = 20
    learning_rate: float = 0.005
    regularization: float = 0.02
    n_epochs: int = 20

    # Federated-specific (optional)
    n_clients: Optional[int] = None
    n_rounds: Optional[int] = None
    batch_size: Optional[int] = None
    aggregation_strategy: Optional[AggregationStrategy] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.n_factors < 1 or self.n_factors > 200:
            raise ValueError(f"n_factors must be 1-200, got {self.n_factors}")
        if self.learning_rate <= 0 or self.learning_rate > 1.0:
            raise ValueError(f"learning_rate must be (0,1.0], got {self.learning_rate}")


# Predefined configurations for testing
CENTRALIZED_DEFAULT = Configuration(n_factors=20, n_epochs=20)
FEDERATED_DEFAULT = Configuration(
    n_factors=20,
    n_epochs=10,
    n_clients=5,
    n_rounds=10,
    aggregation_strategy=AggregationStrategy.FEDAVG,
)
