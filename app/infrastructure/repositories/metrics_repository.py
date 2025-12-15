"""Metrics repository implementation.

Handles persistence of performance metrics using SQLAlchemy.
Provides specialized queries for metrics analysis.
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import PerformanceMetric
from app.infrastructure.models import MetricModel
from app.infrastructure.repositories.base_repository import BaseRepository
from app.utils.exceptions import RepositoryError


class MetricsRepository(BaseRepository[PerformanceMetric, int]):
    """Repository for metrics persistence.

    Provides CRUD operations and specialized queries for
    metrics analysis across experiments.

    Attributes:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    async def add(self, entity: PerformanceMetric, experiment_id: str) -> PerformanceMetric:
        """Persist a new metric.

        Args:
            entity: PerformanceMetric to persist.
            experiment_id: ID of the experiment this metric belongs to.

        Returns:
            The persisted metric.

        Raises:
            RepositoryError: If persistence fails.
        """
        try:
            model = MetricModel(
                experiment_id=experiment_id,
                name=entity.name,
                value=entity.value,
                context=entity.context,
                round_number=entity.round_number,
                client_id=entity.client_id,
            )
            self._session.add(model)
            await self._session.flush()
            return entity
        except Exception as e:
            raise RepositoryError(f"Failed to add metric: {e}") from e

    async def add_batch(
        self, metrics: List[PerformanceMetric], experiment_id: str
    ) -> List[PerformanceMetric]:
        """Persist multiple metrics in batch.

        Args:
            metrics: List of metrics to persist.
            experiment_id: ID of the experiment.

        Returns:
            List of persisted metrics.

        Raises:
            RepositoryError: If persistence fails.
        """
        try:
            models = [
                MetricModel(
                    experiment_id=experiment_id,
                    name=metric.name,
                    value=metric.value,
                    context=metric.context,
                    round_number=metric.round_number,
                    client_id=metric.client_id,
                )
                for metric in metrics
            ]
            self._session.add_all(models)
            await self._session.flush()
            return metrics
        except Exception as e:
            raise RepositoryError(f"Failed to add metrics batch: {e}") from e

    async def get_by_id(self, entity_id: int) -> Optional[PerformanceMetric]:
        """Retrieve a metric by ID.

        Args:
            entity_id: Metric primary key.

        Returns:
            PerformanceMetric if found, None otherwise.
        """
        stmt = select(MetricModel).where(MetricModel.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def get_all(self) -> List[PerformanceMetric]:
        """Retrieve all metrics.

        Returns:
            List of all metrics.
        """
        stmt = select(MetricModel).order_by(MetricModel.recorded_at)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_experiment(self, experiment_id: str) -> List[PerformanceMetric]:
        """Retrieve all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            List of metrics for the experiment.
        """
        stmt = (
            select(MetricModel)
            .where(MetricModel.experiment_id == experiment_id)
            .order_by(MetricModel.round_number, MetricModel.recorded_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_experiment_and_name(
        self, experiment_id: str, metric_name: str
    ) -> List[PerformanceMetric]:
        """Retrieve metrics by experiment and metric name.

        Args:
            experiment_id: Experiment UUID.
            metric_name: Name of metric (e.g., 'rmse', 'loss').

        Returns:
            List of matching metrics.
        """
        stmt = (
            select(MetricModel)
            .where(
                MetricModel.experiment_id == experiment_id,
                MetricModel.name == metric_name,
            )
            .order_by(MetricModel.round_number, MetricModel.recorded_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_client_metrics(
        self, experiment_id: str, client_id: str
    ) -> List[PerformanceMetric]:
        """Retrieve metrics for a specific client.

        Args:
            experiment_id: Experiment UUID.
            client_id: Client identifier.

        Returns:
            List of metrics for the client.
        """
        stmt = (
            select(MetricModel)
            .where(
                MetricModel.experiment_id == experiment_id,
                MetricModel.client_id == client_id,
            )
            .order_by(MetricModel.round_number, MetricModel.recorded_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_round_metrics(
        self, experiment_id: str, round_number: int
    ) -> List[PerformanceMetric]:
        """Retrieve metrics for a specific round.

        Args:
            experiment_id: Experiment UUID.
            round_number: Communication round number.

        Returns:
            List of metrics for the round.
        """
        stmt = (
            select(MetricModel)
            .where(
                MetricModel.experiment_id == experiment_id,
                MetricModel.round_number == round_number,
            )
            .order_by(MetricModel.recorded_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_metric_stats(
        self, experiment_id: str, metric_name: str
    ) -> dict:
        """Get aggregate statistics for a metric.

        Args:
            experiment_id: Experiment UUID.
            metric_name: Name of metric.

        Returns:
            Dict with min, max, avg, count.
        """
        stmt = select(
            func.min(MetricModel.value).label("min"),
            func.max(MetricModel.value).label("max"),
            func.avg(MetricModel.value).label("avg"),
            func.count(MetricModel.id).label("count"),
        ).where(
            MetricModel.experiment_id == experiment_id,
            MetricModel.name == metric_name,
        )
        result = await self._session.execute(stmt)
        row = result.one()

        return {
            "min": row.min,
            "max": row.max,
            "avg": float(row.avg) if row.avg else None,
            "count": row.count,
        }

    async def update(self, entity: PerformanceMetric) -> PerformanceMetric:
        """Update a metric (not typically used).

        Args:
            entity: Metric to update.

        Raises:
            NotImplementedError: Metrics are typically immutable.
        """
        raise NotImplementedError("Metrics are immutable once recorded")

    async def delete(self, entity_id: int) -> bool:
        """Delete a metric by ID.

        Args:
            entity_id: Metric primary key.

        Returns:
            True if deleted, False if not found.
        """
        stmt = select(MetricModel).where(MetricModel.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def delete_by_experiment(self, experiment_id: str) -> int:
        """Delete all metrics for an experiment.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            Number of metrics deleted.
        """
        stmt = select(MetricModel).where(MetricModel.experiment_id == experiment_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        count = len(models)
        for model in models:
            await self._session.delete(model)

        await self._session.flush()
        return count

    async def exists(self, entity_id: int) -> bool:
        """Check if metric exists.

        Args:
            entity_id: Metric primary key.

        Returns:
            True if exists, False otherwise.
        """
        stmt = select(MetricModel.id).where(MetricModel.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_entity(self, model: MetricModel) -> PerformanceMetric:
        """Convert SQLAlchemy model to domain entity.

        Args:
            model: MetricModel from database.

        Returns:
            PerformanceMetric domain entity.
        """
        return PerformanceMetric(
            name=model.name,
            value=model.value,
            context=model.context,
            round_number=model.round_number,
            client_id=model.client_id,
        )
