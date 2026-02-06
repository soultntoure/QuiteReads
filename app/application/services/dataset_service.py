"""Dataset service.

Orchestrates dataset upload, preprocessing, and metadata retrieval.
Uses file-based persistence (no database).
"""

import json
import logging
from pathlib import Path
from typing import Optional

from app.application.data.preprocessing import (
    PreprocessingConfig,
    run_preprocessing_pipeline,
)
from app.application.data.preprocessing_status import (
    get_status,
    update_status,
    PreprocessingStatus,
)
from app.utils.exceptions import DataPreprocessError

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class DatasetService:
    """Service for dataset upload and preprocessing operations."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"

    def is_dataset_loaded(self) -> bool:
        return (self.processed_dir / "metadata.json").exists()

    def get_metadata(self) -> Optional[dict]:
        metadata_path = self.processed_dir / "metadata.json"
        if not metadata_path.exists():
            return None
        with open(metadata_path, "r") as f:
            return json.load(f)

    def get_preprocessing_status(self) -> PreprocessingStatus:
        return get_status()

    def save_uploaded_file(self, content: bytes) -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        dest = self.raw_dir / "uploaded_interactions.json"
        dest.write_bytes(content)
        logger.info(f"Saved uploaded file ({len(content)} bytes) to {dest}")
        return dest

    def run_preprocessing(
        self,
        min_ratings: int,
        val_ratio: float,
        test_ratio: float,
        seed: int,
    ) -> dict:
        """Run preprocessing synchronously (called from background thread)."""
        raw_path = self.raw_dir / "uploaded_interactions.json"
        if not raw_path.exists():
            raise DataPreprocessError("No uploaded file found. Upload a dataset first.")

        config = PreprocessingConfig(
            min_user_ratings=min_ratings,
            min_item_ratings=min_ratings,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=seed,
        )

        def progress_callback(step: str, step_number: int, message: str) -> None:
            update_status(
                status="processing",
                step=step,
                step_number=step_number,
                message=message,
            )

        result = run_preprocessing_pipeline(
            raw_path=raw_path,
            output_dir=self.data_dir,
            config=config,
            progress_callback=progress_callback,
        )

        update_status(
            status="completed",
            step="done",
            step_number=6,
            message="Preprocessing completed successfully.",
        )

        return result
