"""
Experiment schemas.

Pydantic models for experiment creation, updates, and responses.
"""

from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from app.utils.types import AggregationStrategy as DomainAggregationStrategy
if TYPE_CHECKING:
    from app.core.experiments import Experiment
    from app.core.configuration import Configuration as DomainConfiguration
    from app.core.metrics import ExperimentMetrics as DomainExperimentMetrics


class ExperimentType(str, Enum):
    CENTRALIZED = "centralized"
    FEDERATED = "federated"

    def to_domain_value(self) -> str:
        """Convert API ExperimentType to domain experiment_type string.

        Returns:
            String value for domain experiment_type field.
        """
        return self.value


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def to_domain(self) -> "DomainExperimentStatus":
        """Convert API ExperimentStatus to domain ExperimentStatus.

        Returns:
            Domain ExperimentStatus enum value.
        """
        from app.utils.types import ExperimentStatus as DomainStatus

        mapping = {
            ExperimentStatus.PENDING: DomainStatus.PENDING,
            ExperimentStatus.RUNNING: DomainStatus.RUNNING,
            ExperimentStatus.COMPLETED: DomainStatus.COMPLETED,
            ExperimentStatus.FAILED: DomainStatus.FAILED,
        }
        return mapping[self]


class AggregationStrategy(str, Enum):
    """Supported federated aggregation strategies.
    
    Only strategies that are fully implemented in the domain layer should be listed here.
    When adding new strategies, ensure they are also added to app.utils.types.AggregationStrategy
    and the mapping in to_domain() below.
    """
    FEDAVG = "fedavg"

    def to_domain(self) -> "DomainAggregationStrategy":
        """Convert schema AggregationStrategy to domain AggregationStrategy.
        
        Raises:
            ValueError: If the strategy is not supported in the domain layer.
        """
        
        
        mapping = {
            AggregationStrategy.FEDAVG: DomainAggregationStrategy.FEDAVG,
        }
        
        domain_strategy = mapping.get(self)
        if domain_strategy is None:
            supported = [s.value for s in mapping.keys()]
            raise ValueError(
                f"Aggregation strategy '{self.value}' is not yet supported. "
                f"Supported strategies: {supported}"
            )
        
        return domain_strategy
    
    @classmethod
    def from_domain(cls, domain_strategy: "DomainAggregationStrategy") -> "AggregationStrategy":
        """Convert domain AggregationStrategy to API AggregationStrategy.
        
        Args:
            domain_strategy: Domain AggregationStrategy enum value
        
        Returns:
            API AggregationStrategy enum value
        
        Raises:
            ValueError: If the domain strategy is not supported in the API layer.
        """
        mapping = {
            DomainAggregationStrategy.FEDAVG: cls.FEDAVG,
        }
        
        api_strategy = mapping.get(domain_strategy)
        if api_strategy is None:
            supported = [s.name for s in mapping.keys()]
            raise ValueError(
                f"Domain aggregation strategy '{domain_strategy.name}' is not yet supported in API. "
                f"Supported strategies: {supported}"
            )
        
        return api_strategy


class ConfigurationSchema(BaseModel):
    """Shared configuration schema for both centralized and federated experiments"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "matrix_factorization"
            }
        }
    )

    learning_rate: float = Field(..., gt=0, le=1, description="Learning rate must be between 0 and 1")
    batch_size: int = Field(..., gt=0, description="Batch size must be positive")
    epochs: int = Field(..., gt=0, description="Number of epochs must be positive")
    model_type: str = Field(..., min_length=1, description="Type of model to train")

    @classmethod
    def from_domain(cls, config: "DomainConfiguration") -> "ConfigurationSchema":
        """Convert domain Configuration to schema.

        Args:
            config: Domain Configuration entity

        Returns:
            ConfigurationSchema instance
        """
        return cls(
            learning_rate=config.learning_rate,
            batch_size=config.batch_size if config.batch_size else 32,
            epochs=config.n_epochs,
            model_type=config.model_type.value,
        )


class CreateCentralizedExperimentRequest(BaseModel):
    """Request to create a centralized experiment"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "name": "Centralized Matrix Factorization Exp 1",
                "config": {
                    "learning_rate": 0.01,
                    "batch_size": 32,
                    "epochs": 10,
                    "model_type": "matrix_factorization"
                }
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=255, description="Experiment name")
    config: ConfigurationSchema = Field(..., description="Training configuration")

    def to_domain_config(self) -> "DomainConfiguration":
        """Convert request DTO to domain Configuration.

        Returns:
            Domain Configuration entity with centralized defaults.
        """
        from app.core.configuration import Configuration
        return Configuration(
            learning_rate=self.config.learning_rate,
            n_factors=20,
            regularization=0.02,
            n_epochs=self.config.epochs,
        )


class CreateFederatedExperimentRequest(BaseModel):
    """Request to create a federated experiment"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "name": "Federated Matrix Factorization Exp 1",
                "config": {
                    "learning_rate": 0.01,
                    "batch_size": 32,
                    "epochs": 5,
                    "model_type": "matrix_factorization"
                },
                "n_clients": 5,
                "n_rounds": 20,
                "aggregation_strategy": "FedAvg"
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=255, description="Experiment name")
    config: ConfigurationSchema = Field(..., description="Training configuration")
    n_clients: int = Field(..., gt=0, description="Number of clients must be positive")
    n_rounds: int = Field(..., gt=0, description="Number of rounds must be positive")
    aggregation_strategy: AggregationStrategy = Field(..., description="Federated aggregation strategy")

    def to_domain_config(self) -> "DomainConfiguration":
        """Convert request DTO to domain Configuration.

        Returns:
            Domain Configuration entity with federated settings.
        """
        from app.core.configuration import Configuration
        return Configuration(
            learning_rate=self.config.learning_rate,
            n_factors=20,
            regularization=0.02,
            n_epochs=self.config.epochs,
            n_clients=self.n_clients,
            n_rounds=self.n_rounds,
            batch_size=self.config.batch_size,
            aggregation_strategy=self.aggregation_strategy.to_domain(),
        )


class CompleteExperimentRequest(BaseModel):
    """Request to mark experiment as completed with final metrics"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "final_rmse": 0.45,
                "final_mae": 0.32,
                "training_time_seconds": 3600.5
            }
        }
    )

    final_rmse: float = Field(..., ge=0, description="Final RMSE score")
    final_mae: float = Field(..., ge=0, description="Final MAE score")
    training_time_seconds: float = Field(..., gt=0, description="Total training time in seconds")


class ExperimentMetricsSchema(BaseModel):
    """Final metrics for experiment response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "final_rmse": 0.45,
                "final_mae": 0.32,
                "training_time_seconds": 3600.5
            }
        }
    )

    final_rmse: Optional[float] = Field(None, ge=0, description="Final RMSE score")
    final_mae: Optional[float] = Field(None, ge=0, description="Final MAE score")
    training_time_seconds: Optional[float] = Field(None, ge=0, description="Total training time in seconds")

    @classmethod
    def from_domain(cls, metrics: Optional["DomainExperimentMetrics"]) -> "ExperimentMetricsSchema":
        """Convert domain ExperimentMetrics to schema.

        Args:
            metrics: Domain ExperimentMetrics entity or None

        Returns:
            ExperimentMetricsSchema instance
        """
        if not metrics:
            return cls()

        return cls(
            final_rmse=metrics.rmse,
            final_mae=metrics.mae,
            training_time_seconds=metrics.training_time_seconds,
        )


class ExperimentResponse(BaseModel):
    """Unified response for both centralized and federated experiments"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "id": 1,
                "name": "Centralized Matrix Factorization Exp 1",
                "type": "centralized",
                "status": "completed",
                "config": {
                    "learning_rate": 0.01,
                    "batch_size": 32,
                    "epochs": 10,
                    "model_type": "matrix_factorization"
                },
                "metrics": {
                    "final_rmse": 0.45,
                    "final_mae": 0.32,
                    "training_time_seconds": 3600.5
                },
                "n_clients": None,
                "n_rounds": None,
                "aggregation_strategy": None,
                "created_at": "2025-12-19T10:30:00",
                "updated_at": "2025-12-19T14:30:00"
            }
        }
    )

    id: str = Field(..., description="Experiment ID (UUID)")
    name: str = Field(..., description="Experiment name")
    type: ExperimentType = Field(..., description="Type of experiment (centralized or federated)")
    status: ExperimentStatus = Field(..., description="Current status of the experiment")
    config: ConfigurationSchema = Field(..., description="Training configuration")
    metrics: ExperimentMetricsSchema = Field(default_factory=ExperimentMetricsSchema, description="Final metrics")
    n_clients: Optional[int] = Field(None, ge=1, description="Number of clients (federated only)")
    n_rounds: Optional[int] = Field(None, ge=1, description="Number of rounds (federated only)")
    aggregation_strategy: Optional[AggregationStrategy] = Field(None, description="Aggregation strategy (federated only)")
    created_at: datetime = Field(..., description="Timestamp when experiment was created")
    updated_at: datetime = Field(..., description="Timestamp when experiment was last updated")

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Serialize datetime to ISO format"""
        return dt.isoformat()

    @classmethod
    def from_domain(cls, experiment: "Experiment") -> "ExperimentResponse":
        """Convert domain Experiment entity to response schema.

        Args:
            experiment: Domain Experiment entity (CentralizedExperiment or FederatedExperiment)

        Returns:
            ExperimentResponse instance
        """
        # Import here to avoid circular imports
        from app.core.experiments import FederatedExperiment

        return cls(
            id=experiment.experiment_id,
            name=experiment.name,
            type=ExperimentType(experiment.experiment_type),
            status=ExperimentStatus(experiment.status.value),
            config=ConfigurationSchema.from_domain(experiment.config),
            metrics=ExperimentMetricsSchema.from_domain(experiment.metrics),
            n_clients=experiment.n_clients if isinstance(experiment, FederatedExperiment) else None,
            n_rounds=experiment.n_rounds if isinstance(experiment, FederatedExperiment) else None,
            aggregation_strategy=(
                AggregationStrategy.from_domain(experiment.aggregation_strategy)
                if isinstance(experiment, FederatedExperiment)
                else None
            ),
            created_at=experiment.created_at,
            updated_at=experiment.completed_at if experiment.completed_at else experiment.created_at,
        )


class ExperimentListResponse(BaseModel):
    """Wrapper for experiment list responses"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "count": 2,
                "experiments": [
                    {
                        "id": 1,
                        "name": "Centralized Matrix Factorization Exp 1",
                        "type": "centralized",
                        "status": "completed",
                        "config": {
                            "learning_rate": 0.01,
                            "batch_size": 32,
                            "epochs": 10,
                            "model_type": "matrix_factorization"
                        },
                        "metrics": {
                            "final_rmse": 0.45,
                            "final_mae": 0.32,
                            "training_time_seconds": 3600.5
                        },
                        "n_clients": None,
                        "n_rounds": None,
                        "aggregation_strategy": None,
                        "created_at": "2025-12-19T10:30:00",
                        "updated_at": "2025-12-19T14:30:00"
                    }
                ]
            }
        }
    )

    count: int = Field(..., ge=0, description="Total number of experiments")
    experiments: List[ExperimentResponse] = Field(..., description="List of experiments")
