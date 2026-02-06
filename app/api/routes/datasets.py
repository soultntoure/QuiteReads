from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pathlib import Path
import shutil
import logging
from typing import Optional
from pydantic import BaseModel

from app.application.data.preprocessing import (
    run_preprocessing_pipeline,
    PreprocessingConfig
)

router = APIRouter()
logger = logging.getLogger(__name__)

class PreprocessingResponse(BaseModel):
    message: str
    config: dict
    statistics: dict
    n_iterations: int

@router.post("/upload", response_model=PreprocessingResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    min_user_ratings: int = Form(20),
    min_item_ratings: int = Form(20),
    val_ratio: float = Form(0.1),
    test_ratio: float = Form(0.2)
):
    """
    Upload a raw dataset (JSON Lines) and trigger the preprocessing pipeline.
    This replaces the current active dataset.
    """
    # Validation
    if not file.filename.endswith('.json') and not file.filename.endswith('.jsonl'):
         # Allow .json or .jsonl (Goodreads data is often named .json but is jsonl)
         pass 

    # Define paths
    # We save to data/raw/uploaded_interactions.json to distinguish from the default one
    # or should we overwrite the default? User said "replace default dataset".
    # The default path in preprocessing.py is data/raw/goodreads_interactions_poetry.json
    # Let's use a standard name for the uploaded file so the pipeline can use it consistently.
    
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_path = raw_dir / "uploaded_interactions.json"

    try:
        # Save uploaded file
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded file to {target_path}")

        # Configure preprocessing
        config = PreprocessingConfig(
            min_user_ratings=min_user_ratings,
            min_item_ratings=min_item_ratings,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=42 # Fixed seed for now
        )

        # Run preprocessing synchronously (as requested, blocking operation is acceptable)
        # We output to "data" directory, same as default
        output_dir = Path("data")
        
        # Note: run_preprocessing_pipeline writes to data/processed and data/splits
        # It handles the logic.
        
        results = run_preprocessing_pipeline(
            raw_path=target_path,
            output_dir=output_dir,
            config=config
        )

        return {
            "message": "Dataset processed and activated successfully",
            "config": results["config"],
            "statistics": results["statistics"],
            "n_iterations": results["n_iterations"]
        }

    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dataset processing failed: {str(e)}")
