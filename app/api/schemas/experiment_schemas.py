"""
Experiment schemas.

Pydantic models for experiment creation, updates, and responses.
"""

from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List
from enum import Enum
from datetime import datetime


class ExperimentType(str, Enum):
    CENTRALIZED = "centralized"
    FEDERATED = "federated"


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AggregationStrategy(str, Enum):
    FedAvg = "FedAvg"
    FedProx = "FedProx"
    FedAdam = "FedAdam"


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

    id: int = Field(..., description="Experiment ID")
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
