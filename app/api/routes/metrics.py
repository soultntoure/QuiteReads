"""Metrics API routes.

Endpoints for recording and retrieving experiment performance metrics.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.schemas.metrics_schemas import (
    AddMetricRequest,
    AddMetricsBatchRequest,
    MetricResponse,
    MetricListResponse,
)
from app.api.dependencies import get_metrics_service
from app.application.services import MetricsService
from app.core.metrics import PerformanceMetric

router = APIRouter(prefix="/experiments", tags=["metrics"])

# Type alias for dependency injection
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]

@router.post("/{experiment_id}/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def add_metric(
    experiment_id: str,
    request: AddMetricRequest,
    service: MetricsServiceDep,
):
    """Add a single performance metric to an experiment."""
    metric = await service.add_metric(
        experiment_id=experiment_id,
        name=request.name,
        value=request.value,
        round_number=request.round_number,
        client_id=request.client_id,
    )
    return MetricResponse.model_validate(metric)

@router.post("/{experiment_id}/metrics/batch", response_model=list[MetricResponse], status_code=status.HTTP_201_CREATED)
async def add_metrics_batch(
    experiment_id: str,
    request: AddMetricsBatchRequest,
    service: MetricsServiceDep,
):
    """Add multiple performance metrics to an experiment in a batch."""
    metrics_list = [
        PerformanceMetric(
            name=m.name,
            value=m.value,
            experiment_id=experiment_id,
            round_number=m.round_number,
            client_id=m.client_id,
        )
        for m in request.metrics
    ]
    result = await service.add_metrics_batch(experiment_id, metrics_list)
    return [MetricResponse.model_validate(m) for m in result]

@router.get("/{experiment_id}/metrics", response_model=MetricListResponse)
async def list_metrics(
    experiment_id: str,
    service: MetricsServiceDep,
    name: Optional[str] = Query(None, description="Filter by metric name"),
    client_id: Optional[str] = Query(None, description="Filter by client ID (federated only)"),
    round_number: Optional[int] = Query(None, ge=0, description="Filter by round number (federated only)"),
    context: Optional[str] = Query(None, description="Filter by context (training, validation, centralized_test, client_aggregated)"),
):
    """List metrics for an experiment with optional filters."""
    # Apply filters in order of specificity
    if client_id and round_number is not None:
        # Get all metrics, then filter manually for both client and round
        all_metrics = await service.get_experiment_metrics(experiment_id)
        metrics = [
            m for m in all_metrics
            if m.client_id == client_id and m.round_number == round_number
        ]
        if name:
            metrics = [m for m in metrics if m.name == name]
    elif client_id:
        metrics = await service.get_client_metrics(experiment_id, client_id)
        if name:
            metrics = [m for m in metrics if m.name == name]
    elif round_number is not None:
        metrics = await service.get_round_metrics(experiment_id, round_number)
        if name:
            metrics = [m for m in metrics if m.name == name]
    elif name:
        metrics = await service.get_metrics_by_name(experiment_id, name)
    else:
        metrics = await service.get_experiment_metrics(experiment_id)

    # Apply context filter if specified
    if context:
        metrics = [m for m in metrics if m.context == context]

    return MetricListResponse(
        count=len(metrics),
        metrics=[MetricResponse.model_validate(m) for m in metrics]
    )

@router.delete("/{experiment_id}/metrics", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_experiment_metrics(
    experiment_id: str,
    service: MetricsServiceDep,
):
    """Delete all metrics for an experiment."""
    await service.delete_experiment_metrics(experiment_id)
