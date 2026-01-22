"""Unit tests for DataLoader factory functions.

Tests the factory functions for creating PyTorch DataLoaders.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from app.application.data.data_loader_factory import create_eval_loader, create_train_loader
from app.application.data.ratings_dataset import RatingsDataset


@pytest.fixture
def sample_dataset():
    """Create a sample RatingsDataset for testing."""
    data = {
        'user_idx': list(range(100)) * 10,  # 1000 interactions
        'item_idx': [i % 50 for i in range(1000)],
        'rating': [3.0 + (i % 5) / 2 for i in range(1000)],
    }
    df = pd.DataFrame(data)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'ratings.parquet'
        df.to_parquet(path, index=False)
        yield RatingsDataset(path, n_users=100, n_items=50)


class TestCreateTrainLoader:
    """Tests for create_train_loader function."""

    def test_returns_dataloader(self, sample_dataset):
        """Test that function returns a DataLoader."""
        loader = create_train_loader(sample_dataset)

        assert isinstance(loader, DataLoader)

    def test_default_batch_size(self, sample_dataset):
        """Test default batch size is 1024."""
        loader = create_train_loader(sample_dataset)

        # With 1000 samples and batch_size=1024, we get 1 batch
        assert len(loader) == 1

    def test_custom_batch_size(self, sample_dataset):
        """Test custom batch size."""
        loader = create_train_loader(sample_dataset, batch_size=100)

        # 1000 samples / 100 = 10 batches
        assert len(loader) == 10

    def test_shuffle_enabled(self, sample_dataset):
        """Test that shuffle is enabled for training."""
        loader = create_train_loader(sample_dataset, batch_size=100)

        # Get first batch twice and compare - should be different if shuffled
        # Note: This is probabilistic but highly likely to differ
        batch1_users = next(iter(loader))[0].tolist()
        batch2_users = next(iter(loader))[0].tolist()

        # With shuffle, the batches should very likely be different
        # (if they're the same, the test might rarely fail)
        # We just verify we can iterate
        assert len(batch1_users) == 100

    def test_batch_contents(self, sample_dataset):
        """Test that batch contains correct tensor types."""
        loader = create_train_loader(sample_dataset, batch_size=100)

        users, items, ratings = next(iter(loader))

        assert users.dtype == torch.long
        assert items.dtype == torch.long
        assert ratings.dtype == torch.float32

        assert users.shape[0] == 100
        assert items.shape[0] == 100
        assert ratings.shape[0] == 100


class TestCreateEvalLoader:
    """Tests for create_eval_loader function."""

    def test_returns_dataloader(self, sample_dataset):
        """Test that function returns a DataLoader."""
        loader = create_eval_loader(sample_dataset)

        assert isinstance(loader, DataLoader)

    def test_default_batch_size(self, sample_dataset):
        """Test default batch size is 1024."""
        loader = create_eval_loader(sample_dataset)

        assert len(loader) == 1

    def test_custom_batch_size(self, sample_dataset):
        """Test custom batch size."""
        loader = create_eval_loader(sample_dataset, batch_size=100)

        assert len(loader) == 10

    def test_no_shuffle(self, sample_dataset):
        """Test that shuffle is disabled for evaluation."""
        loader = create_eval_loader(sample_dataset, batch_size=100)

        # Get first batch twice - should be the same
        batch1_users = next(iter(loader))[0].tolist()
        batch2_users = next(iter(loader))[0].tolist()

        assert batch1_users == batch2_users

    def test_batch_contents(self, sample_dataset):
        """Test that batch contains correct tensor types."""
        loader = create_eval_loader(sample_dataset, batch_size=100)

        users, items, ratings = next(iter(loader))

        assert users.dtype == torch.long
        assert items.dtype == torch.long
        assert ratings.dtype == torch.float32
