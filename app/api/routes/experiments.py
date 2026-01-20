"""Experiment API routes.

Endpoints for managing centralized and federated learning experiments.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response, status
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

router = APIRouter(prefix="/experiments", tags=["experiments"])

# Type alias for dependency injection
ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]


@router.post("/centralized", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_centralized_experiment(request: CreateCentralizedExperimentRequest, service: ExperimentServiceDep):
    """Create a new centralized experiment"""
    experiment = await service.create_centralized_experiment(
        name=request.name,
        config=request.to_domain_config(),
    )
    return ExperimentResponse.from_domain(experiment)


@router.post("/federated", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_federated_experiment(request: CreateFederatedExperimentRequest, service: ExperimentServiceDep):
    """Create a new federated experiment"""
    config = request.to_domain_config()

    experiment = await service.create_federated_experiment(
        name=request.name,
        config=config,
        n_clients=request.n_clients,
        n_rounds=request.n_rounds,
        aggregation_strategy=request.aggregation_strategy.to_domain(),
    )
    return ExperimentResponse.from_domain(experiment)


@router.get("/", response_model=ExperimentListResponse)
async def list_experiments(
    service: ExperimentServiceDep,
    status_filter: ExperimentStatus | None = Query(default=None, description="Filter by status"),
    type_filter: ExperimentType | None = Query(default=None, description="Filter by type"),
):
    """List all experiments with optional filters"""
    if status_filter and type_filter:
        experiments = await service.get_experiments_by_status_and_type(
            status_filter.to_domain(), type_filter.to_domain_value()
        )
    elif status_filter:
        experiments = await service.get_experiments_by_status(status_filter.to_domain())
    elif type_filter:
        experiments = await service.get_experiments_by_type(type_filter.to_domain_value())
    else:
        experiments = await service.get_all_experiments()

    return ExperimentListResponse(
        count=len(experiments),
        experiments=[ExperimentResponse.from_domain(e) for e in experiments]
    )



@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str,service: ExperimentServiceDep):
    """Get a single experiment by ID"""
    experiment = await service.get_experiment_by_id(experiment_id)
    return ExperimentResponse.from_domain(experiment)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(experiment_id: str,service: ExperimentServiceDep):
    """Start an experiment (transition to RUNNING status)"""
    experiment = await service.start_experiment(experiment_id)
    return ExperimentResponse.from_domain(experiment)


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(experiment_id: str, request: CompleteExperimentRequest,service: ExperimentServiceDep):
    """Complete an experiment with final metrics"""
    experiment = await service.complete_experiment(
        experiment_id,
        final_rmse=request.final_rmse,
        final_mae=request.final_mae,
        training_time_seconds=request.training_time_seconds,
    )
    return ExperimentResponse.from_domain(experiment)


@router.post("/{experiment_id}/fail", response_model=ExperimentResponse)
async def fail_experiment(experiment_id: str, service: ExperimentServiceDep):
    """Mark experiment as failed"""
    experiment = await service.fail_experiment(experiment_id)
    return ExperimentResponse.from_domain(experiment)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: str, service: ExperimentServiceDep):
    """Delete an experiment"""
    await service.delete_experiment(experiment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

