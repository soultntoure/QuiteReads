from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AddMetricRequest(BaseModel):
    name: str = Field(..., min_length=1)
    value: float = Field(...)
    round_number: Optional[int] = Field(None, ge=0)
    client_id: Optional[int] = Field(None, ge=0)
    timestamp: Optional[datetime] = Field(None)


class AddMetricsBatchRequest(BaseModel):
    metrics: List[AddMetricRequest] = Field(..., min_items=1)


class MetricResponse(BaseModel):
    id: int
    experiment_id: int
    name: str
    value: float
    round_number: Optional[int] = None
    client_id: Optional[int] = None
    timestamp: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MetricListResponse(BaseModel):
    count: int
    metrics: List[MetricResponse]


class MetricStatisticsResponse(BaseModel):
    metric_name: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RoundConvergenceData(BaseModel):
    round_number: int
    avg_loss: float
    min_loss: float
    max_loss: float
    num_clients_reported: int


class ConvergenceAnalysisResponse(BaseModel):
    experiment_id: int
    metric_name: str
    total_rounds: int
    rounds_data: List[RoundConvergenceData]
    convergence_trend: str


class ClientPerformanceData(BaseModel):
    client_id: int
    avg_metric_value: float
    best_metric_value: float
    latest_metric_value: Optional[float] = None
    num_updates: int


class ClientComparisonResponse(BaseModel):
    experiment_id: int
    metric_name: str
    total_clients: int
    clients_data: List[ClientPerformanceData]
    best_performing_client_id: Optional[int] = None
    worst_performing_client_id: Optional[int] = None
