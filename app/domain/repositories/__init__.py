"""Repository interfaces.

Defines protocols for repository layer following the Repository pattern.
"""

from app.domain.repositories.interfaces import (
    IExperimentRepository,
    IMetricsRepository,
)

__all__ = [
    "IExperimentRepository",
    "IMetricsRepository",
]
