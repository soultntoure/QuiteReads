"""Unit tests for RatingsDataset.

Tests the pure PyTorch Dataset for rating interactions.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest
import torch

from app.application.data.ratings_dataset import RatingsDataset


@pytest.fixture
def sample_parquet_file():
    """Create a temporary parquet file with sample rating data."""
    data = {
        'user_idx': [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
        'item_idx': [0, 1, 0, 2, 1, 3, 2, 4, 3, 4],
        'rating': [4.0, 3.0, 5.0, 2.0, 4.0, 3.0, 5.0, 4.0, 3.0, 2.0],
    }
    df = pd.DataFrame(data)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'ratings.parquet'
        df.to_parquet(path, index=False)
        yield path


class TestRatingsDataset:
    """Tests for RatingsDataset class."""

    def test_load_parquet(self, sample_parquet_file):
        """Test loading data from parquet file."""
        dataset = RatingsDataset(sample_parquet_file)

        assert len(dataset) == 10
        assert dataset.n_users == 5  # Inferred from max user_idx + 1
        assert dataset.n_items == 5  # Inferred from max item_idx + 1

    def test_explicit_dimensions(self, sample_parquet_file):
        """Test providing explicit n_users and n_items."""
        dataset = RatingsDataset(
            sample_parquet_file,
            n_users=100,
            n_items=50,
        )

        assert dataset.n_users == 100
        assert dataset.n_items == 50

    def test_getitem_returns_tensors(self, sample_parquet_file):
        """Test that __getitem__ returns correct tensor types."""
        dataset = RatingsDataset(sample_parquet_file)

        user, item, rating = dataset[0]

        assert isinstance(user, torch.Tensor)
        assert isinstance(item, torch.Tensor)
        assert isinstance(rating, torch.Tensor)

        assert user.dtype == torch.long
        assert item.dtype == torch.long
        assert rating.dtype == torch.float32

    def test_getitem_values(self, sample_parquet_file):
        """Test that __getitem__ returns correct values."""
        dataset = RatingsDataset(sample_parquet_file)

        user, item, rating = dataset[0]

        assert user.item() == 0
        assert item.item() == 0
        assert rating.item() == 4.0

    def test_rating_mean(self, sample_parquet_file):
        """Test rating_mean property."""
        dataset = RatingsDataset(sample_parquet_file)

        # Expected: (4+3+5+2+4+3+5+4+3+2) / 10 = 3.5
        assert dataset.rating_mean == pytest.approx(3.5)

    def test_rating_std(self, sample_parquet_file):
        """Test rating_std property."""
        dataset = RatingsDataset(sample_parquet_file)

        # Should be positive and reasonable
        assert dataset.rating_std > 0
        assert dataset.rating_std < 2.0

    def test_local_users(self, sample_parquet_file):
        """Test local_users property."""
        dataset = RatingsDataset(sample_parquet_file)

        local_users = dataset.local_users

        assert isinstance(local_users, set)
        assert local_users == {0, 1, 2, 3, 4}

    def test_num_local_users(self, sample_parquet_file):
        """Test num_local_users property."""
        dataset = RatingsDataset(sample_parquet_file)

        assert dataset.num_local_users == 5

    def test_missing_columns_raises_error(self):
        """Test that missing columns raise ValueError."""
        data = {
            'user_id': [0, 1],  # Wrong column name
            'item_idx': [0, 1],
            'rating': [4.0, 3.0],
        }
        df = pd.DataFrame(data)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'bad_ratings.parquet'
            df.to_parquet(path, index=False)

            with pytest.raises(ValueError, match="Missing columns"):
                RatingsDataset(path)

    def test_iteration(self, sample_parquet_file):
        """Test iterating over dataset."""
        dataset = RatingsDataset(sample_parquet_file)

        count = 0
        for user, item, rating in dataset:
            count += 1
            assert isinstance(user, torch.Tensor)
            assert isinstance(item, torch.Tensor)
            assert isinstance(rating, torch.Tensor)

        assert count == 10
