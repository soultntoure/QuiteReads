"""Unit tests for DatasetLoader.

Tests the high-level data loading interface.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from torch.utils.data import DataLoader

from app.application.data.dataset_loader import DatasetLoader, DatasetMetadata
from app.application.data.ratings_dataset import RatingsDataset
from app.core.entities import Dataset


@pytest.fixture
def sample_data_dir():
    """Create a complete sample data directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Create directories
        processed_dir = data_dir / 'processed'
        splits_dir = data_dir / 'splits'
        processed_dir.mkdir()
        splits_dir.mkdir()

        # Create sample data
        train_data = {
            'user_idx': [0, 0, 1, 1, 2, 2, 3, 3],
            'item_idx': [0, 1, 0, 2, 1, 3, 2, 4],
            'rating': [4.0, 3.0, 5.0, 2.0, 4.0, 3.0, 5.0, 4.0],
        }
        val_data = {
            'user_idx': [0, 1, 2, 3],
            'item_idx': [2, 3, 4, 0],
            'rating': [3.0, 4.0, 2.0, 5.0],
        }
        test_data = {
            'user_idx': [0, 1, 2, 3],
            'item_idx': [3, 4, 0, 1],
            'rating': [4.0, 3.0, 5.0, 2.0],
        }
        indexed_data = {
            'user_idx': [0, 0, 1, 1, 2, 2, 3, 3, 0, 1, 2, 3, 0, 1, 2, 3],
            'item_idx': [0, 1, 0, 2, 1, 3, 2, 4, 2, 3, 4, 0, 3, 4, 0, 1],
            'rating': [4.0, 3.0, 5.0, 2.0, 4.0, 3.0, 5.0, 4.0, 3.0, 4.0, 2.0, 5.0, 4.0, 3.0, 5.0, 2.0],
        }

        # Save parquet files
        pd.DataFrame(train_data).to_parquet(splits_dir / 'train.parquet', index=False)
        pd.DataFrame(val_data).to_parquet(splits_dir / 'val.parquet', index=False)
        pd.DataFrame(test_data).to_parquet(splits_dir / 'test.parquet', index=False)
        pd.DataFrame(indexed_data).to_parquet(processed_dir / 'interactions_indexed.parquet', index=False)

        # Create metadata
        metadata = {
            'statistics': {
                'filtered_users': 4,
                'filtered_items': 5,
                'sparsity': 0.2,
            },
            'train_size': 8,
            'val_size': 4,
            'test_size': 4,
        }

        # Create ID mappings
        user_mapping = {'user_0': 0, 'user_1': 1, 'user_2': 2, 'user_3': 3}
        item_mapping = {'item_0': 0, 'item_1': 1, 'item_2': 2, 'item_3': 3, 'item_4': 4}

        # Save JSON files
        with open(processed_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
        with open(processed_dir / 'user_mapping.json', 'w') as f:
            json.dump(user_mapping, f)
        with open(processed_dir / 'item_mapping.json', 'w') as f:
            json.dump(item_mapping, f)

        yield data_dir


class TestDatasetLoader:
    """Tests for DatasetLoader class."""

    def test_verify_data_exists(self, sample_data_dir):
        """Test verify_data_exists passes with valid data."""
        loader = DatasetLoader(sample_data_dir)
        loader.verify_data_exists()  # Should not raise

    def test_verify_data_exists_missing_metadata(self):
        """Test verify_data_exists raises for missing metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = DatasetLoader(tmpdir)
            with pytest.raises(FileNotFoundError, match="Metadata file not found"):
                loader.verify_data_exists()

    def test_load(self, sample_data_dir):
        """Test load() successfully loads metadata."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        assert loader.n_users == 4
        assert loader.n_items == 5

    def test_access_before_load_raises_error(self, sample_data_dir):
        """Test accessing properties before load() raises RuntimeError."""
        loader = DatasetLoader(sample_data_dir)

        with pytest.raises(RuntimeError, match="load\\(\\) must be called"):
            _ = loader.n_users

    def test_n_users(self, sample_data_dir):
        """Test n_users property."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        assert loader.n_users == 4

    def test_n_items(self, sample_data_dir):
        """Test n_items property."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        assert loader.n_items == 5

    def test_global_mean(self, sample_data_dir):
        """Test global_mean property computed from training data."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        # Training data ratings: [4.0, 3.0, 5.0, 2.0, 4.0, 3.0, 5.0, 4.0]
        # Mean = 30 / 8 = 3.75
        assert loader.global_mean == pytest.approx(3.75)

    def test_user_mapping(self, sample_data_dir):
        """Test user_mapping property."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        mapping = loader.user_mapping

        assert isinstance(mapping, dict)
        assert len(mapping) == 4
        assert mapping['user_0'] == 0

    def test_item_mapping(self, sample_data_dir):
        """Test item_mapping property."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        mapping = loader.item_mapping

        assert isinstance(mapping, dict)
        assert len(mapping) == 5
        assert mapping['item_0'] == 0

    def test_get_metadata(self, sample_data_dir):
        """Test get_metadata() returns DatasetMetadata."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        metadata = loader.get_metadata()

        assert isinstance(metadata, DatasetMetadata)
        assert metadata.n_users == 4
        assert metadata.n_items == 5
        assert metadata.train_size == 8
        assert metadata.val_size == 4
        assert metadata.test_size == 4

    def test_get_model_init_args(self, sample_data_dir):
        """Test get_model_init_args() returns correct dict."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        args = loader.get_model_init_args()

        assert 'n_users' in args
        assert 'n_items' in args
        assert 'global_mean' in args
        assert args['n_users'] == 4
        assert args['n_items'] == 5

    def test_get_domain_dataset(self, sample_data_dir):
        """Test get_domain_dataset() returns Dataset entity."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        dataset = loader.get_domain_dataset()

        assert isinstance(dataset, Dataset)
        assert len(dataset.df) == 16  # All indexed interactions
        assert dataset.user_mapping is not None
        assert dataset.book_mapping is not None

    def test_get_train_loader(self, sample_data_dir):
        """Test get_train_loader() returns DataLoader."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        train_loader = loader.get_train_loader(batch_size=4)

        assert isinstance(train_loader, DataLoader)
        assert len(train_loader) == 2  # 8 samples / 4 batch_size

    def test_get_val_loader(self, sample_data_dir):
        """Test get_val_loader() returns DataLoader."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        val_loader = loader.get_val_loader(batch_size=4)

        assert isinstance(val_loader, DataLoader)
        assert len(val_loader) == 1  # 4 samples / 4 batch_size

    def test_get_test_loader(self, sample_data_dir):
        """Test get_test_loader() returns DataLoader."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        test_loader = loader.get_test_loader(batch_size=4)

        assert isinstance(test_loader, DataLoader)
        assert len(test_loader) == 1

    def test_get_train_dataset(self, sample_data_dir):
        """Test get_train_dataset() returns RatingsDataset."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        dataset = loader.get_train_dataset()

        assert isinstance(dataset, RatingsDataset)
        assert len(dataset) == 8

    def test_get_val_dataset(self, sample_data_dir):
        """Test get_val_dataset() returns RatingsDataset."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        dataset = loader.get_val_dataset()

        assert isinstance(dataset, RatingsDataset)
        assert len(dataset) == 4

    def test_get_test_dataset(self, sample_data_dir):
        """Test get_test_dataset() returns RatingsDataset."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        dataset = loader.get_test_dataset()

        assert isinstance(dataset, RatingsDataset)
        assert len(dataset) == 4

    def test_datasets_have_correct_dimensions(self, sample_data_dir):
        """Test all datasets have same n_users and n_items."""
        loader = DatasetLoader(sample_data_dir)
        loader.load()

        train = loader.get_train_dataset()
        val = loader.get_val_dataset()
        test = loader.get_test_dataset()

        # All should use global dimensions
        assert train.n_users == 4
        assert train.n_items == 5
        assert val.n_users == 4
        assert val.n_items == 5
        assert test.n_users == 4
        assert test.n_items == 5
