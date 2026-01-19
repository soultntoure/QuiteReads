"""API dependencies.

Dependency injection setup for API routes and services.
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure import get_session
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.application.services import ExperimentService, MetricsService


def get_experiment_service(
    db: Annotated[AsyncSession, Depends(get_session)]
) -> ExperimentService:
    """Dependency injection for experiment service.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        ExperimentService instance with repositories wired
    """
    experiment_repo = ExperimentRepository(db)
    metrics_repo = MetricsRepository(db)
    return ExperimentService(experiment_repo, metrics_repo)


def get_metrics_service(
    db: Annotated[AsyncSession, Depends(get_session)]
) -> MetricsService:
    """Dependency injection for metrics service.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        MetricsService instance with repositories wired
    """
    experiment_repo = ExperimentRepository(db)
    metrics_repo = MetricsRepository(db)
    return MetricsService(metrics_repo, experiment_repo)
