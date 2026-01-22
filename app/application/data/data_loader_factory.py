"""DataLoader factory functions.

Factory functions for creating PyTorch DataLoaders from RatingsDataset.
Replaces Lightning DataModule's DataLoader creation.

Adapted from research repo: src/data/datamodule.py (RatingsDataModule methods)
"""

from torch.utils.data import DataLoader

from app.application.data.ratings_dataset import RatingsDataset


def create_train_loader(
    dataset: RatingsDataset,
    batch_size: int = 1024,
    num_workers: int = 0,
    pin_memory: bool = True,
) -> DataLoader:
    """Create DataLoader for training data.

    Training DataLoader has shuffle=True for stochastic gradient descent.

    Args:
        dataset: RatingsDataset containing training data
        batch_size: Number of samples per batch (default: 1024)
        num_workers: Number of worker processes for data loading (default: 0)
        pin_memory: Pin memory for faster GPU transfer (default: True)

    Returns:
        DataLoader with shuffled training data
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )


def create_eval_loader(
    dataset: RatingsDataset,
    batch_size: int = 1024,
    num_workers: int = 0,
    pin_memory: bool = True,
) -> DataLoader:
    """Create DataLoader for evaluation data (validation or test).

    Evaluation DataLoader has shuffle=False for deterministic evaluation.

    Args:
        dataset: RatingsDataset containing evaluation data
        batch_size: Number of samples per batch (default: 1024)
        num_workers: Number of worker processes for data loading (default: 0)
        pin_memory: Pin memory for faster GPU transfer (default: True)

    Returns:
        DataLoader with evaluation data (no shuffling)
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )
