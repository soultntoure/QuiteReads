"""Domain entities.

Core dataclasses representing domain objects.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

import pandas as pd
from scipy.sparse import csr_matrix


@dataclass
class Rating:
    """Single user-book rating interaction."""

    user_id: str
    book_id: str
    rating: float
    timestamp: Optional[str] = None


@dataclass
class Book:
    """Book entity."""

    book_id: str
    title: Optional[str] = None


@dataclass
class Dataset:
    """Goodreads dataset with preprocessing metadata."""

    df: pd.DataFrame  # Raw ratings DataFrame
    user_mapping: Dict[str, int]  # original_user_id -> encoded_index
    book_mapping: Dict[str, int]  # original_book_id -> encoded_index
    sparse_matrix: Optional[csr_matrix] = None  # User-item sparse matrix


@dataclass
class LocalUserData:
    """User data partition for federated client."""

    client_id: str
    user_ids: list[str]  # Original user IDs in this partition
    ratings_df: pd.DataFrame  # Ratings for these users
    n_ratings: int = field(init=False)

    def __post_init__(self):
        """Auto-compute number of ratings."""
        self.n_ratings = len(self.ratings_df)
