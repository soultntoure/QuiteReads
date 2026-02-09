"""In-memory training status tracker.

Stores training progress in memory for real-time polling.
Resets on server restart. Tracks one experiment at a time.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# Step labels for centralized experiments
CENTRALIZED_STEPS = [
    "loading_data",
    "initializing",
    "training",
    "validating",
    "saving",
    "done",
]

# Step labels for federated experiments
FEDERATED_STEPS = [
    "loading_data",
    "initializing",
    "training",
    "aggregating",
    "saving",
    "done",
]

# Human-readable step descriptions
STEP_DESCRIPTIONS = {
    "idle": "Waiting to start",
    "loading_data": "Loading and preparing dataset",
    "initializing": "Setting up model and optimizer",
    "training": "Training in progress",
    "validating": "Running validation",
    "aggregating": "Aggregating federated results",
    "saving": "Persisting metrics",
    "done": "Training completed",
}


@dataclass
class TrainingStatus:
    """Current state of experiment training."""

    experiment_id: Optional[str] = None
    experiment_type: Optional[str] = None  # "centralized" or "federated"
    status: str = "idle"  # idle, training, completed, failed
    step: str = "idle"
    step_number: int = 0
    total_steps: int = 0
    message: str = ""
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    current_round: Optional[int] = None  # For federated
    total_rounds: Optional[int] = None  # For federated
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Global status instance
_current_status = TrainingStatus()


def get_status(experiment_id: Optional[str] = None) -> TrainingStatus:
    """Get current training status.
    
    Args:
        experiment_id: If provided, only return status if it matches.
        
    Returns:
        Current training status or idle status if experiment_id doesn't match.
    """
    if experiment_id is not None and _current_status.experiment_id != experiment_id:
        return TrainingStatus()
    return _current_status


def is_training() -> bool:
    """Check if training is currently in progress."""
    return _current_status.status == "training"


def start_training(
    experiment_id: str,
    experiment_type: str,
    total_epochs: Optional[int] = None,
    total_rounds: Optional[int] = None,
) -> None:
    """Start tracking a new training session.
    
    Args:
        experiment_id: UUID of the experiment.
        experiment_type: "centralized" or "federated".
        total_epochs: Total epochs for centralized training.
        total_rounds: Total rounds for federated training.
    """
    global _current_status
    
    steps = CENTRALIZED_STEPS if experiment_type == "centralized" else FEDERATED_STEPS
    
    _current_status = TrainingStatus(
        experiment_id=experiment_id,
        experiment_type=experiment_type,
        status="training",
        step="loading_data",
        step_number=1,
        total_steps=len(steps),
        message=STEP_DESCRIPTIONS["loading_data"],
        total_epochs=total_epochs,
        total_rounds=total_rounds,
    )
    logger.info(f"Training started for experiment {experiment_id} ({experiment_type})")


def update_step(
    step: str,
    message: Optional[str] = None,
    current_epoch: Optional[int] = None,
    current_round: Optional[int] = None,
) -> None:
    """Update the current training step.
    
    Args:
        step: Step label (e.g., "training", "validating").
        message: Optional custom message.
        current_epoch: Current epoch number (1-indexed).
        current_round: Current round number (1-indexed).
    """
    global _current_status
    
    if _current_status.status != "training":
        return
    
    experiment_type = _current_status.experiment_type
    steps = CENTRALIZED_STEPS if experiment_type == "centralized" else FEDERATED_STEPS
    
    try:
        step_number = steps.index(step) + 1
    except ValueError:
        step_number = _current_status.step_number
    
    default_message = STEP_DESCRIPTIONS.get(step, step)
    
    # Build message with epoch/round info
    if current_epoch is not None and _current_status.total_epochs:
        default_message = f"Training epoch {current_epoch}/{_current_status.total_epochs}"
    elif current_round is not None and _current_status.total_rounds:
        default_message = f"Training round {current_round}/{_current_status.total_rounds}"
    
    _current_status = TrainingStatus(
        experiment_id=_current_status.experiment_id,
        experiment_type=_current_status.experiment_type,
        status="training",
        step=step,
        step_number=step_number,
        total_steps=_current_status.total_steps,
        message=message or default_message,
        current_epoch=current_epoch or _current_status.current_epoch,
        total_epochs=_current_status.total_epochs,
        current_round=current_round or _current_status.current_round,
        total_rounds=_current_status.total_rounds,
    )
    logger.debug(f"Training step: [{step_number}/{_current_status.total_steps}] {step}")


def complete_training() -> None:
    """Mark training as completed."""
    global _current_status
    
    steps = CENTRALIZED_STEPS if _current_status.experiment_type == "centralized" else FEDERATED_STEPS
    
    _current_status = TrainingStatus(
        experiment_id=_current_status.experiment_id,
        experiment_type=_current_status.experiment_type,
        status="completed",
        step="done",
        step_number=len(steps),
        total_steps=len(steps),
        message="Training completed successfully",
        current_epoch=_current_status.total_epochs,
        total_epochs=_current_status.total_epochs,
        current_round=_current_status.total_rounds,
        total_rounds=_current_status.total_rounds,
    )
    logger.info(f"Training completed for experiment {_current_status.experiment_id}")


def fail_training(error: str) -> None:
    """Mark training as failed.
    
    Args:
        error: Error message describing the failure.
    """
    global _current_status
    
    _current_status = TrainingStatus(
        experiment_id=_current_status.experiment_id,
        experiment_type=_current_status.experiment_type,
        status="failed",
        step=_current_status.step,
        step_number=_current_status.step_number,
        total_steps=_current_status.total_steps,
        message="Training failed",
        error=error,
        current_epoch=_current_status.current_epoch,
        total_epochs=_current_status.total_epochs,
        current_round=_current_status.current_round,
        total_rounds=_current_status.total_rounds,
    )
    logger.error(f"Training failed for experiment {_current_status.experiment_id}: {error}")


def reset_status() -> None:
    """Reset training status to idle."""
    global _current_status
    _current_status = TrainingStatus()
