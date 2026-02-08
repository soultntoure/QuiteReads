"""Metrics schemas.

Pydantic models for performance metric data structures.
"""

from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

# Request schemas

class AddMetricRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "rmse",
                    "value": 0.842,
                    "round_number": 5,
                    "client_id": "client_2"
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, description="Metric name (e.g., 'train_loss', 'val_rmse')")
    value: float = Field(..., description="Metric value")
    round_number: Optional[int] = Field(None, ge=0, description="Training round number (federated only)")
    client_id: Optional[str] = Field(None, description="Client ID (federated only)")


class AddMetricsBatchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "metrics": [
                        {
                            "name": "rmse",
                            "value": 0.842,
                            "round_number": 5,
                            "client_id": "client_1"
                        },
                        {
                            "name": "mae",
                            "value": 0.656,
                            "round_number": 5,
                            "client_id": "client_1"
                        }
                    ]
                }
            ]
        }
    )

    metrics: List[AddMetricRequest] = Field(..., min_length=1, description="List of metrics to add")


class MetricResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # Allow validation from domain entities (dataclasses)
        json_schema_extra={
            "examples": [
                {
                    "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "rmse",
                    "value": 0.842,
                    "round_number": 5,
                    "client_id": "client_2"
                }
            ]
        }
    )

    experiment_id: str = Field(..., description="Associated experiment ID (UUID)")
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    round_number: Optional[int] = Field(None, description="Training round number (federated only)")
    client_id: Optional[str] = Field(None, description="Client ID (federated only)")
    context: Optional[str] = Field(None, description="Metric context (training, validation, centralized_test, client_aggregated)")


class MetricListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "count": 2,
                    "metrics": [
                        {
                            "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "rmse",
                            "value": 0.842,
                            "round_number": 5,
                            "client_id": "client_2"
                        },
                        {
                            "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "mae",
                            "value": 0.656,
                            "round_number": 5,
                            "client_id": "client_2"
                        }
                    ]
                }
            ]
        }
    )

    count: int = Field(..., ge=0, description="Total number of metrics returned")
    metrics: List[MetricResponse] = Field(..., description="List of metric records")


class MetricStatisticsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "metric_name": "rmse",
                    "count": 100,
                    "min_value": 0.721,
                    "max_value": 1.376,
                    "avg_value": 0.953
                }
            ]
        }
    )

    metric_name: str = Field(..., description="Name of the metric")
    count: int = Field(..., ge=0, description="Total number of records for this metric")
    min_value: float = Field(..., description="Minimum value observed")
    max_value: float = Field(..., description="Maximum value observed")
    avg_value: float = Field(..., description="Average value across all records")


class RoundConvergenceData(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "round_number": 5,
                    "avg_loss": 0.453,
                    "min_loss": 0.321,
                    "max_loss": 0.678,
                    "num_clients_reported": 10
                }
            ]
        }
    )

    round_number: int = Field(..., ge=0, description="Federated learning round number")
    avg_loss: float = Field(..., description="Average loss across all clients in this round")
    min_loss: float = Field(..., description="Minimum loss observed in this round")
    max_loss: float = Field(..., description="Maximum loss observed in this round")
    num_clients_reported: int = Field(..., ge=0, description="Number of clients that reported metrics for this round")


class ConvergenceAnalysisResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                    "metric_name": "rmse",
                    "total_rounds": 20,
                    "rounds_data": [
                        {
                            "round_number": 1,
                            "avg_loss": 1.376,
                            "min_loss": 1.234,
                            "max_loss": 1.523,
                            "num_clients_reported": 10
                        },
                        {
                            "round_number": 20,
                            "avg_loss": 0.842,
                            "min_loss": 0.798,
                            "max_loss": 0.921,
                            "num_clients_reported": 10
                        }
                    ],
                    "convergence_trend": "decreasing"
                }
            ]
        }
    )

    experiment_id: str = Field(..., description="Experiment ID (UUID)")
    metric_name: str = Field(..., description="Metric being analyzed")
    total_rounds: int = Field(..., ge=0, description="Total number of federated learning rounds")
    rounds_data: List[RoundConvergenceData] = Field(..., description="Per-round convergence statistics")
    convergence_trend: str = Field(..., description="Overall trend (e.g., 'decreasing', 'stable', 'increasing')")

# client analytics schemas

class ClientPerformanceData(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "client_id": "client_2",
                    "avg_metric_value": 0.453,
                    "best_metric_value": 0.321,
                    "latest_metric_value": 0.342,
                    "num_updates": 20
                }
            ]
        }
    )

    client_id: str = Field(..., description="Unique client identifier")
    avg_metric_value: float = Field(..., description="Average metric value across all rounds for this client")
    best_metric_value: float = Field(..., description="Best (lowest) metric value achieved by this client")
    latest_metric_value: Optional[float] = Field(None, description="Most recent metric value from this client")
    num_updates: int = Field(..., ge=0, description="Number of times this client reported metrics")


class ClientComparisonResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                    "metric_name": "rmse",
                    "total_clients": 10,
                    "clients_data": [
                        {
                            "client_id": "client_1",
                            "avg_metric_value": 0.956,
                            "best_metric_value": 0.821,
                            "latest_metric_value": 0.842,
                            "num_updates": 20
                        },
                        {
                            "client_id": "client_2",
                            "avg_metric_value": 0.912,
                            "best_metric_value": 0.798,
                            "latest_metric_value": 0.805,
                            "num_updates": 20
                        }
                    ],
                    "best_performing_client_id": "client_2",
                    "worst_performing_client_id": "client_7"
                }
            ]
        }
    )

    experiment_id: str = Field(..., description="Experiment ID (UUID)")
    metric_name: str = Field(..., description="Metric being compared across clients")
    total_clients: int = Field(..., ge=0, description="Total number of clients in the experiment")
    clients_data: List[ClientPerformanceData] = Field(..., description="Performance data for each client")
    best_performing_client_id: Optional[str] = Field(None, description="ID of client with best (lowest) metric value")
    worst_performing_client_id: Optional[str] = Field(None, description="ID of client with worst (highest) metric value")
