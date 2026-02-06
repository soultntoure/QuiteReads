"""Dataset API routes.

Endpoints for uploading datasets, triggering preprocessing,
polling preprocessing status, and retrieving dataset statistics.
"""

import asyncio
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.schemas.dataset_schemas import (
    DatasetMetadataResponse,
    DatasetStatistics,
    PreprocessingStatusResponse,
    UploadResponse,
)
from app.application.data.preprocessing_status import is_processing, update_status
from app.application.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dataset", tags=["dataset"])


def _get_service() -> DatasetService:
    return DatasetService()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_and_preprocess(
    file: UploadFile = File(..., description="JSON Lines file"),
    min_ratings: int = Form(default=20),
    val_ratio: float = Form(default=0.1),
    test_ratio: float = Form(default=0.2),
    seed: int = Form(default=42),
):
    """Upload a dataset file and start preprocessing in the background."""
    if is_processing():
        raise HTTPException(
            status_code=409,
            detail="Preprocessing is already in progress. Please wait.",
        )

    if not file.filename or not file.filename.endswith((".json", ".jsonl")):
        raise HTTPException(
            status_code=422,
            detail="File must be a .json or .jsonl file.",
        )

    service = _get_service()

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    update_status("processing", "uploading", 1, "Uploading file...")
    service.save_uploaded_file(content)

    asyncio.create_task(
        _run_preprocessing_background(service, min_ratings, val_ratio, test_ratio, seed)
    )

    return UploadResponse(
        message="Upload successful. Preprocessing started.",
        status="processing",
    )


async def _run_preprocessing_background(
    service: DatasetService,
    min_ratings: int,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> None:
    """Run preprocessing in a background thread (CPU-bound)."""
    try:
        await asyncio.to_thread(
            service.run_preprocessing, min_ratings, val_ratio, test_ratio, seed
        )
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        update_status("failed", "failed", 0, "Preprocessing failed.", error=str(e))


@router.get("/status", response_model=PreprocessingStatusResponse)
async def get_preprocessing_status():
    """Poll current preprocessing status."""
    s = _get_service().get_preprocessing_status()
    return PreprocessingStatusResponse(
        status=s.status,
        step=s.step,
        step_number=s.step_number,
        total_steps=s.total_steps,
        message=s.message,
        error=s.error,
    )


@router.get("/metadata", response_model=DatasetMetadataResponse)
async def get_dataset_metadata():
    """Get dataset metadata and statistics."""
    service = _get_service()

    if not service.is_dataset_loaded():
        return DatasetMetadataResponse(is_loaded=False)

    metadata = service.get_metadata()
    if metadata is None:
        return DatasetMetadataResponse(is_loaded=False)

    stats_raw = metadata.get("statistics")
    statistics = DatasetStatistics(**stats_raw) if stats_raw else None

    return DatasetMetadataResponse(
        is_loaded=True,
        preprocessing_date=metadata.get("preprocessing_date"),
        config=metadata.get("config"),
        statistics=statistics,
        filter_iterations=metadata.get("filter_iterations"),
        train_size=metadata.get("train_size"),
        val_size=metadata.get("val_size"),
        test_size=metadata.get("test_size"),
    )
