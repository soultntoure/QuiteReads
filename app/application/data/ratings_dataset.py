"""PyTorch Dataset for rating interactions.

Pure PyTorch Dataset for user-item rating data. Loads preprocessed parquet
files containing (user_idx, item_idx, rating) tuples and provides them as
tensors for training.
"""

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import torch
from torch.utils.data import Dataset


class RatingsDataset(Dataset):
    """PyTorch Dataset for user-item rating interactions.

    Loads preprocessed parquet files containing (user_idx, item_idx, rating)
    tuples and provides them as tensors for PyTorch training.

    Attributes:
        users: Tensor of user indices, shape (n_interactions,)
        items: Tensor of item indices, shape (n_interactions,)
        ratings: Tensor of ratings, shape (n_interactions,)
        n_users: Number of unique users (for embedding table size)
        n_items: Number of unique items (for embedding table size)

    Example:
        >>> dataset = RatingsDataset('data/splits/train.parquet')
        >>> len(dataset)
        183034
        >>> user, item, rating = dataset[0]
        >>> user.shape, item.shape, rating.shape
        (torch.Size([]), torch.Size([]), torch.Size([]))
    """

    def __init__(
        self,
        parquet_path: str | Path,
        n_users: Optional[int] = None,
        n_items: Optional[int] = None,
    ):
        """Initialize dataset from parquet file.

        Args:
            parquet_path: Path to parquet file with columns:
                         (user_idx, item_idx, rating)
            n_users: Total number of users (optional, inferred if not provided).
                    Should be provided for consistency across train/val/test.
            n_items: Total number of items (optional, inferred if not provided).
                    Should be provided for consistency across train/val/test.
        """
        self.path = Path(parquet_path)

        # Load data
        df = pd.read_parquet(self.path)

        # Validate columns
        required_cols = {'user_idx', 'item_idx', 'rating'}
        if not required_cols.issubset(df.columns):
            raise ValueError(
                f"Missing columns. Expected {required_cols}, got {set(df.columns)}"
            )

        # Convert to tensors
        self.users = torch.tensor(df['user_idx'].values, dtype=torch.long)
        self.items = torch.tensor(df['item_idx'].values, dtype=torch.long)
        self.ratings = torch.tensor(df['rating'].values, dtype=torch.float32)

        # Store dimensions (important for embedding table initialization)
        # If not provided, infer from data (may underestimate if test has different IDs)
        self.n_users = n_users if n_users is not None else int(self.users.max()) + 1
        self.n_items = n_items if n_items is not None else int(self.items.max()) + 1

        # Track local users (useful for federated scenarios)
        self._local_users: Optional[set] = None

    def __len__(self) -> int:
        """Return number of interactions."""
        return len(self.ratings)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return single interaction as (user_idx, item_idx, rating).

        Args:
            idx: Index of the interaction

        Returns:
            Tuple of (user_idx, item_idx, rating) tensors
        """
        return self.users[idx], self.items[idx], self.ratings[idx]

    @property
    def rating_mean(self) -> float:
        """Mean rating (useful for global bias initialization)."""
        return float(self.ratings.mean())

    @property
    def rating_std(self) -> float:
        """Rating standard deviation."""
        return float(self.ratings.std())

    @property
    def local_users(self) -> set:
        """Set of unique user indices in this dataset."""
        if self._local_users is None:
            self._local_users = set(self.users.unique().tolist())
        return self._local_users

    @property
    def num_local_users(self) -> int:
        """Number of unique users in this dataset."""
        return len(self.local_users)
