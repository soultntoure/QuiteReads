"""In-memory preprocessing status tracker.

Stores preprocessing progress in memory. Resets on server restart.
Single-dataset mode: only one preprocessing operation at a time.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

STEP_LABELS = [
    "uploading",
    "loading",
    "filtering",
    "mapping",
    "splitting",
    "saving",
    "done",
]

TOTAL_STEPS = 6


@dataclass
class PreprocessingStatus:
    """Current state of the preprocessing pipeline."""

    status: str = "idle"
    step: str = "idle"
    step_number: int = 0
    total_steps: int = TOTAL_STEPS
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


_current_status = PreprocessingStatus()


def get_status() -> PreprocessingStatus:
    return _current_status


def is_processing() -> bool:
    return _current_status.status == "processing"


def update_status(
    status: str,
    step: str,
    step_number: int,
    message: str,
    error: Optional[str] = None,
) -> None:
    global _current_status
    _current_status = PreprocessingStatus(
        status=status,
        step=step,
        step_number=step_number,
        total_steps=TOTAL_STEPS,
        message=message,
        error=error,
    )
    logger.info(f"Preprocessing status: [{step_number}/{TOTAL_STEPS}] {step} - {message}")


def reset_status() -> None:
    global _current_status
    _current_status = PreprocessingStatus()
