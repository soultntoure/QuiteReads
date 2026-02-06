"""Dataset schemas.

Pydantic models for dataset upload, preprocessing status, and statistics responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PreprocessingStatusResponse(BaseModel):
    """Current preprocessing status for polling."""

    status: str = Field(..., description="idle | processing | completed | failed")
    step: str = Field(..., description="Current step name")
    step_number: int = Field(..., ge=0)
    total_steps: int
    message: str = ""
    error: Optional[str] = None


class DatasetStatistics(BaseModel):
    """Before/after statistics from preprocessing."""

    original_interactions: int
    original_users: int
    original_items: int
    filtered_interactions: int
    filtered_users: int
    filtered_items: int
    sparsity: float
    sparsity_percent: str
    density_percent: str
    rating_mean: float
    rating_std: float
    rating_min: int
    rating_max: int
    retention_rate: str


class DatasetMetadataResponse(BaseModel):
    """Full dataset metadata including config, statistics, and split sizes."""

    is_loaded: bool
    preprocessing_date: Optional[str] = None
    config: Optional[dict] = None
    statistics: Optional[DatasetStatistics] = None
    filter_iterations: Optional[int] = None
    train_size: Optional[int] = None
    val_size: Optional[int] = None
    test_size: Optional[int] = None


class UploadResponse(BaseModel):
    """Response after successful file upload + preprocessing start."""

    message: str
    status: str
