"""API dependencies.

Dependency injection setup for API routes and services.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure import get_session
from app.infrastructure.repositories import ExperimentRepository, MetricsRepository
from app.application.services import ExperimentService, MetricsService


async def get_experiment_service(db: AsyncSession) -> ExperimentService:
    """Dependency injection for experiment service.
    
    Args:
        db: Database session
        
    Returns:
        ExperimentService instance with repositories wired
    """
    experiment_repo = ExperimentRepository(db)
    metrics_repo = MetricsRepository(db)
    return ExperimentService(experiment_repo, metrics_repo)


async def get_metrics_service(db: AsyncSession) -> MetricsService:
    """Dependency injection for metrics service.
    
    Args:
        db: Database session
        
    Returns:
        MetricsService instance with repositories wired
    """
    experiment_repo = ExperimentRepository(db)
    metrics_repo = MetricsRepository(db)
    return MetricsService(metrics_repo, experiment_repo)
