"""API dependencies.

Dependency injection setup for API routes and services.
"""
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure import get_session
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.application.services import ExperimentService, MetricsService
from app.application.services.dataset_service import DatasetService


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


def require_dataset_loaded() -> None:
    """Raises 409 if no processed dataset exists."""
    if not DatasetService().is_dataset_loaded():
        raise HTTPException(
            status_code=409,
            detail="No processed dataset available. Upload and process a dataset first.",
        )
