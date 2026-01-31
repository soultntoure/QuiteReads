"""Training module for centralized and federated learning.

This module contains trainers and simulation managers for executing
machine learning experiments.
"""

from app.application.training.centralized_trainer import (
    CentralizedTrainer,
    TrainingResult,
)
from app.application.training.federated_simulation_manager import (
    FederatedSimulationManager,
    FederatedSimulationResult,
)

__all__ = [
    "CentralizedTrainer",
    "TrainingResult",
    "FederatedSimulationManager",
    "FederatedSimulationResult",
]
