"""Performance metrics for experiments."""

# trunk-ignore(ruff/F401)
from dataclasses import dataclass, field
from typing import List, Optional

# trunk-ignore(ruff/F401)
from app.utils.types import ExperimentStatus


@dataclass
class PerformanceMetric:
    """Single performance measurement."""

    name: str  # 'rmse', 'mae', 'training_time', 'loss'
    value: float
    context: Optional[str] = None  # 'global', 'client_1', 'round_5'
    round_number: Optional[int] = None
    client_id: Optional[str] = None


@dataclass
class ExperimentMetrics:
    """Complete metrics for one experiment."""

    rmse: float
    mae: float
    training_time_seconds: float
    metrics_per_round: Optional[List[PerformanceMetric]] = None  # For FL

    @property
    def is_federated(self) -> bool:
        """Check if this has per-round metrics (FL)."""
        return self.metrics_per_round is not None
