"""Metrics API routes.

Endpoints for recording and retrieving experiment performance metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.infrastructure import get_session
from app.api.schemas.metrics_schemas import (
    AddMetricRequest,
    AddMetricsBatchRequest,
    MetricResponse,
    MetricListResponse,
)
from app.api.dependencies import get_metrics_service
from app.core.metrics import PerformanceMetric
from app.utils.exceptions import EntityNotFoundError

router = APIRouter(prefix="/experiments", tags=["metrics"])

@router.post("/{experiment_id}/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def add_metric(
    experiment_id: str,
    request: AddMetricRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        service = await get_metrics_service(db)
        metric = await service.add_metric(
            experiment_id=experiment_id,
            name=request.name,
            value=request.value,
            round_number=request.round_number,
            client_id=request.client_id,
        )
        return MetricResponse.from_orm(metric)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{experiment_id}/metrics/batch", response_model=list[MetricResponse], status_code=status.HTTP_201_CREATED)
async def add_metrics_batch(
    experiment_id: str,
    request: AddMetricsBatchRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        service = await get_metrics_service(db)
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
        return [MetricResponse.from_orm(m) for m in result]
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{experiment_id}/metrics", response_model=MetricListResponse)
async def list_metrics(
    experiment_id: str,
    name: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    round_number: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = await get_metrics_service(db)
        if name:
            metrics = await service.get_metrics_by_name(experiment_id, name)
        else:
            metrics = await service.get_experiment_metrics(experiment_id)
        return MetricListResponse(count=len(metrics), metrics=[MetricResponse.from_orm(m) for m in metrics])
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{experiment_id}/metrics", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment_metrics(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        service = await get_metrics_service(db)
        await service.delete_experiment_metrics(experiment_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
