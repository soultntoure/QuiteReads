"""Experiment repository implementation.

Handles persistence of experiment domain entities using SQLAlchemy.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.configuration import Configuration
from app.core.experiments import (
    CentralizedExperiment,
    Experiment,
    FederatedExperiment,
)
from app.core.metrics import ExperimentMetrics, PerformanceMetric
from app.infrastructure.models import ExperimentModel, MetricModel
from app.infrastructure.repositories.base_repository import BaseRepository
from app.utils.exceptions import EntityNotFoundError, RepositoryError
from app.utils.types import AggregationStrategy, ExperimentStatus


class ExperimentRepository(BaseRepository[Experiment, str]):
    """Repository for experiment persistence.

    Converts between domain entities and SQLAlchemy models,
    handling polymorphic experiment types (centralized/federated).

    Attributes:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    async def add(self, entity: Experiment) -> Experiment:
        """Persist a new experiment.

        Args:
            entity: Experiment domain entity.

        Returns:
            The persisted experiment.

        Raises:
            RepositoryError: If persistence fails.
        """
        try:
            model = self._to_model(entity)
            self._session.add(model)
            await self._session.flush()
            return entity
        except Exception as e:
            raise RepositoryError(f"Failed to add experiment: {e}") from e

    async def get_by_id(self, entity_id: str) -> Optional[Experiment]:
        """Retrieve an experiment by ID.

        Args:
            entity_id: Experiment UUID.

        Returns:
            Experiment if found, None otherwise.
        """
        stmt = select(ExperimentModel).where(ExperimentModel.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def get_all(self) -> List[Experiment]:
        """Retrieve all experiments.

        Returns:
            List of all experiments.
        """
        stmt = select(ExperimentModel).order_by(ExperimentModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_status(self, status: ExperimentStatus) -> List[Experiment]:
        """Retrieve experiments by status.

        Args:
            status: Experiment status to filter by.

        Returns:
            List of experiments with given status.
        """
        stmt = (
            select(ExperimentModel)
            .where(ExperimentModel.status == status)
            .order_by(ExperimentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_type(self, experiment_type: str) -> List[Experiment]:
        """Retrieve experiments by type.

        Args:
            experiment_type: 'centralized' or 'federated'.

        Returns:
            List of experiments of given type.
        """
        stmt = (
            select(ExperimentModel)
            .where(ExperimentModel.experiment_type == experiment_type)
            .order_by(ExperimentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def update(self, entity: Experiment) -> Experiment:
        """Update an existing experiment.

        Args:
            entity: Experiment with updated fields.

        Returns:
            Updated experiment.

        Raises:
            EntityNotFoundError: If experiment not found.
            RepositoryError: If update fails.
        """
        stmt = select(ExperimentModel).where(ExperimentModel.id == entity.experiment_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            raise EntityNotFoundError(f"Experiment {entity.experiment_id} not found")

        try:
            self._update_model(model, entity)
            await self._session.flush()
            return entity
        except Exception as e:
            raise RepositoryError(f"Failed to update experiment: {e}") from e

    async def delete(self, entity_id: str) -> bool:
        """Delete an experiment by ID.

        Args:
            entity_id: Experiment UUID.

        Returns:
            True if deleted, False if not found.
        """
        stmt = select(ExperimentModel).where(ExperimentModel.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def exists(self, entity_id: str) -> bool:
        """Check if experiment exists.

        Args:
            entity_id: Experiment UUID.

        Returns:
            True if exists, False otherwise.
        """
        stmt = select(ExperimentModel.id).where(ExperimentModel.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_model(self, entity: Experiment) -> ExperimentModel:
        """Convert domain entity to SQLAlchemy model.

        Args:
            entity: Experiment domain entity.

        Returns:
            ExperimentModel for persistence.
        """
        config_dict = {
            "model_type": entity.config.model_type.value,
            "n_factors": entity.config.n_factors,
            "learning_rate": entity.config.learning_rate,
            "regularization": entity.config.regularization,
            "n_epochs": entity.config.n_epochs,
        }

        model = ExperimentModel(
            id=entity.experiment_id,
            name=entity.name,
            experiment_type=entity.experiment_type,
            status=entity.status,
            created_at=entity.created_at,
            completed_at=entity.completed_at,
            config=config_dict,
            final_rmse=entity.metrics.rmse if entity.metrics else None,
            final_mae=entity.metrics.mae if entity.metrics else None,
            training_time_seconds=(
                entity.metrics.training_time_seconds if entity.metrics else None
            ),
        )

        # Add federated-specific fields
        if isinstance(entity, FederatedExperiment):
            model.n_clients = entity.n_clients
            model.n_rounds = entity.n_rounds
            model.aggregation_strategy = entity.aggregation_strategy

        # Add training metrics
        metrics = entity.get_training_timeline()
        for metric in metrics:
            metric_model = MetricModel(
                name=metric.name,
                value=metric.value,
                context=metric.context,
                round_number=metric.round_number,
                client_id=metric.client_id,
            )
            model.metrics.append(metric_model)

        # Add client metrics for federated experiments
        if isinstance(entity, FederatedExperiment):
            for client_id, client_metrics in entity.client_metrics.items():
                for metric in client_metrics:
                    metric_model = MetricModel(
                        name=metric.name,
                        value=metric.value,
                        context="client",
                        round_number=metric.round_number,
                        client_id=client_id,
                    )
                    model.metrics.append(metric_model)

        return model

    def _to_entity(self, model: ExperimentModel) -> Experiment:
        """Convert SQLAlchemy model to domain entity.

        Args:
            model: ExperimentModel from database.

        Returns:
            Experiment domain entity.
        """
        # Rebuild configuration
        from app.utils.types import ModelType

        config = Configuration(
            model_type=ModelType(model.config["model_type"]),
            n_factors=model.config["n_factors"],
            learning_rate=model.config["learning_rate"],
            regularization=model.config["regularization"],
            n_epochs=model.config["n_epochs"],
        )

        # Rebuild final metrics if present
        final_metrics = None
        if model.final_rmse is not None:
            final_metrics = ExperimentMetrics(
                rmse=model.final_rmse,
                mae=model.final_mae or 0.0,
                training_time_seconds=model.training_time_seconds or 0.0,
            )

        # Separate training metrics from client metrics
        training_metrics: List[PerformanceMetric] = []
        client_metrics: dict[str, List[PerformanceMetric]] = {}

        for metric_model in model.metrics:
            pm = PerformanceMetric(
                name=metric_model.name,
                value=metric_model.value,
                experiment_id=metric_model.experiment_id,
                context=metric_model.context,
                round_number=metric_model.round_number,
                client_id=metric_model.client_id,
            )
            if metric_model.context == "client" and metric_model.client_id:
                if metric_model.client_id not in client_metrics:
                    client_metrics[metric_model.client_id] = []
                client_metrics[metric_model.client_id].append(pm)
            else:
                training_metrics.append(pm)

        # Create appropriate entity type
        if model.experiment_type == "federated":
            entity = FederatedExperiment(
                name=model.name,
                config=config,
                experiment_id=model.id,
                status=model.status,
                metrics=final_metrics,
                created_at=model.created_at,
                completed_at=model.completed_at,
                n_clients=model.n_clients or 5,
                n_rounds=model.n_rounds or 10,
                aggregation_strategy=model.aggregation_strategy or AggregationStrategy.FEDAVG,
                round_metrics=training_metrics,
                client_metrics=client_metrics,
            )
        else:
            entity = CentralizedExperiment(
                name=model.name,
                config=config,
                experiment_id=model.id,
                status=model.status,
                metrics=final_metrics,
                created_at=model.created_at,
                completed_at=model.completed_at,
                epoch_metrics=training_metrics,
            )

        return entity

    def _update_model(self, model: ExperimentModel, entity: Experiment) -> None:
        """Update model fields from entity.

        Args:
            model: Existing model to update.
            entity: Entity with new values.
        """
        model.name = entity.name
        model.status = entity.status
        model.completed_at = entity.completed_at

        if entity.metrics:
            model.final_rmse = entity.metrics.rmse
            model.final_mae = entity.metrics.mae
            model.training_time_seconds = entity.metrics.training_time_seconds

        # Clear and re-add metrics
        model.metrics.clear()

        metrics = entity.get_training_timeline()
        for metric in metrics:
            metric_model = MetricModel(
                name=metric.name,
                value=metric.value,
                context=metric.context,
                round_number=metric.round_number,
                client_id=metric.client_id,
            )
            model.metrics.append(metric_model)

        if isinstance(entity, FederatedExperiment):
            model.n_clients = entity.n_clients
            model.n_rounds = entity.n_rounds
            model.aggregation_strategy = entity.aggregation_strategy

            for client_id, client_metrics in entity.client_metrics.items():
                for metric in client_metrics:
                    metric_model = MetricModel(
                        name=metric.name,
                        value=metric.value,
                        context="client",
                        round_number=metric.round_number,
                        client_id=client_id,
                    )
                    model.metrics.append(metric_model)
