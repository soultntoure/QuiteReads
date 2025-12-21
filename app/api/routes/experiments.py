"""Experiment management routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure import get_session
from app.core.configuration import Configuration
from app.api.schemas.experiment_schemas import (
    CreateCentralizedExperimentRequest,
    CreateFederatedExperimentRequest,
    CompleteExperimentRequest,
    ExperimentResponse,
    ExperimentListResponse,
    ExperimentType,
    ExperimentStatus,
)
from app.api.dependencies import get_experiment_service
from app.application.services import ExperimentService
from app.utils.exceptions import EntityNotFoundError, ConfigurationError
from app.utils.types import AggregationStrategy, ExperimentStatus as ExperimentStatusEnum

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/centralized", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_centralized_experiment(
    request: CreateCentralizedExperimentRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a new centralized experiment"""
    try:
        service = await get_experiment_service(db)
        
        config = Configuration(
            learning_rate=request.config.learning_rate,
            n_factors=20,
            regularization=0.02,
            n_epochs=request.config.epochs,
        )
        
        experiment = await service.create_centralized_experiment(
            name=request.name,
            config=config,
        )
        return ExperimentResponse.from_orm(experiment)
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/federated", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_federated_experiment(
    request: CreateFederatedExperimentRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a new federated experiment"""
    try:
        service = await get_experiment_service(db)
        
        agg_strategy = AggregationStrategy.FEDAVG
        
        config = Configuration(
            learning_rate=request.config.learning_rate,
            n_factors=20,
            regularization=0.02,
            n_epochs=request.config.epochs,
            n_clients=request.n_clients,
            n_rounds=request.n_rounds,
            batch_size=request.config.batch_size,
            aggregation_strategy=agg_strategy,
        )
        
        experiment = await service.create_federated_experiment(
            name=request.name,
            config=config,
            n_clients=request.n_clients,
            n_rounds=request.n_rounds,
            aggregation_strategy=agg_strategy,
        )
        return ExperimentResponse.from_orm(experiment)
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    status_filter: ExperimentStatus = Query(None, description="Filter by status"),
    type_filter: ExperimentType = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_session),
):
    """List all experiments with optional filters"""
    service = await get_experiment_service(db)
    
    try:
        if status_filter and type_filter:
            by_status = await service.get_experiments_by_status(ExperimentStatusEnum[status_filter.value.upper()])
            experiments = [e for e in by_status if e.experiment_type == type_filter.value]
        elif status_filter:
            experiments = await service.get_experiments_by_status(ExperimentStatusEnum[status_filter.value.upper()])
        elif type_filter:
            experiments = await service.get_experiments_by_type(type_filter.value)
        else:
            experiments = await service.get_all_experiments()
        
        return ExperimentListResponse(
            count=len(experiments),
            experiments=[ExperimentResponse.from_orm(e) for e in experiments]
        )
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get a single experiment by ID"""
    try:
        service = await get_experiment_service(db)
        experiment = await service.get_experiment_by_id(experiment_id)
        return ExperimentResponse.from_orm(experiment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Start an experiment (transition to RUNNING status)"""
    try:
        service = await get_experiment_service(db)
        experiment = await service.start_experiment(experiment_id)
        return ExperimentResponse.from_orm(experiment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(
    experiment_id: str,
    request: CompleteExperimentRequest,
    db: AsyncSession = Depends(get_session),
):
    """Complete an experiment with final metrics"""
    try:
        service = await get_experiment_service(db)
        experiment = await service.complete_experiment(
            experiment_id,
            final_rmse=request.final_rmse,
            final_mae=request.final_mae,
            training_time_seconds=request.training_time_seconds,
        )
        return ExperimentResponse.from_orm(experiment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{experiment_id}/fail", response_model=ExperimentResponse)
async def fail_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Mark experiment as failed"""
    try:
        service = await get_experiment_service(db)
        experiment = await service.fail_experiment(experiment_id)
        return ExperimentResponse.from_orm(experiment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete an experiment"""
    try:
        service = await get_experiment_service(db)
        await service.delete_experiment(experiment_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
