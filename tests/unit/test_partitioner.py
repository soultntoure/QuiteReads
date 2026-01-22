"""Unit tests for UserPartitioner.

Tests the IID user-based data partitioning for federated learning.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from app.application.data.partitioner import (
    PartitionConfig,
    PartitionResult,
    UserPartitioner,
    verify_partitions,
)
from app.core.entities import LocalUserData


@pytest.fixture
def sample_data_dir():
    """Create a sample data directory with train/val splits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        splits_dir = data_dir / 'splits'
        splits_dir.mkdir()

        # Create sample train data with 10 users, 5 items
        train_data = {
            'user_idx': [u for u in range(10) for _ in range(5)],  # 50 interactions
            'item_idx': [i % 5 for _ in range(10) for i in range(5)],
            'rating': [3.0 + (i % 3) for i in range(50)],
        }

        # Create sample val data
        val_data = {
            'user_idx': [u for u in range(10) for _ in range(2)],  # 20 interactions
            'item_idx': [(i + 1) % 5 for _ in range(10) for i in range(2)],
            'rating': [4.0 + (i % 2) for i in range(20)],
        }

        pd.DataFrame(train_data).to_parquet(splits_dir / 'train.parquet', index=False)
        pd.DataFrame(val_data).to_parquet(splits_dir / 'val.parquet', index=False)

        yield data_dir


class TestPartitionConfig:
    """Tests for PartitionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PartitionConfig()

        assert config.num_clients == 10
        assert config.seed == 42

    def test_custom_values(self):
        """Test custom configuration values."""
        config = PartitionConfig(num_clients=5, seed=123)

        assert config.num_clients == 5
        assert config.seed == 123


class TestUserPartitioner:
    """Tests for UserPartitioner class."""

    def test_partition_creates_client_directories(self, sample_data_dir):
        """Test partition creates correct number of client directories."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            result = partitioner.partition(sample_data_dir, output_dir)

            # Check directories exist
            for i in range(5):
                assert (output_dir / f'client_{i}').exists()

    def test_partition_returns_result(self, sample_data_dir):
        """Test partition returns PartitionResult."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            result = partitioner.partition(sample_data_dir, output_dir)

            assert isinstance(result, PartitionResult)
            assert result.num_clients == 5
            assert len(result.users_per_client) == 5
            assert len(result.interactions_per_client) == 5

    def test_partition_saves_config(self, sample_data_dir):
        """Test partition saves configuration file."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            result = partitioner.partition(sample_data_dir, output_dir)

            assert result.config_path.exists()

            with open(result.config_path) as f:
                config = json.load(f)

            assert config['num_clients'] == 5
            assert 'total_users' in config
            assert 'total_items' in config
            assert 'global_mean' in config

    def test_partition_creates_client_data_files(self, sample_data_dir):
        """Test each client directory has train and val parquet files."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            for i in range(5):
                client_dir = output_dir / f'client_{i}'
                assert (client_dir / 'train.parquet').exists()
                assert (client_dir / 'val.parquet').exists()

    def test_partition_users_are_disjoint(self, sample_data_dir):
        """Test users are exclusively assigned to one client."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            all_users = set()
            for i in range(5):
                client_train = pd.read_parquet(output_dir / f'client_{i}' / 'train.parquet')
                client_users = set(client_train['user_idx'].unique())

                # Check no overlap
                assert all_users.isdisjoint(client_users)
                all_users.update(client_users)

    def test_partition_all_users_assigned(self, sample_data_dir):
        """Test all users are assigned to some client."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            result = partitioner.partition(sample_data_dir, output_dir)

            total_users = sum(result.users_per_client)
            assert total_users == 10  # We have 10 users in sample data

    def test_partition_reproducible_with_seed(self, sample_data_dir):
        """Test partitioning is reproducible with same seed."""
        results = []

        for _ in range(2):
            with tempfile.TemporaryDirectory() as output_dir:
                output_dir = Path(output_dir)

                partitioner = UserPartitioner(PartitionConfig(num_clients=5, seed=42))
                result = partitioner.partition(sample_data_dir, output_dir)
                results.append(result.users_per_client)

        assert results[0] == results[1]

    def test_partition_too_many_clients_raises_error(self, sample_data_dir):
        """Test error when num_clients > num_users."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=100))

            with pytest.raises(ValueError, match="exceeds unique users"):
                partitioner.partition(sample_data_dir, output_dir)

    def test_get_client_paths(self, sample_data_dir):
        """Test get_client_paths returns correct paths."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            train_path, val_path = partitioner.get_client_paths(0)

            assert train_path == output_dir / 'client_0' / 'train.parquet'
            assert val_path == output_dir / 'client_0' / 'val.parquet'

    def test_get_client_paths_before_partition_raises_error(self):
        """Test get_client_paths raises error if partition() not called."""
        partitioner = UserPartitioner()

        with pytest.raises(RuntimeError, match="partition\\(\\) must be called"):
            partitioner.get_client_paths(0)

    def test_get_client_paths_invalid_client_id(self, sample_data_dir):
        """Test get_client_paths raises error for invalid client_id."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            with pytest.raises(ValueError, match="out of range"):
                partitioner.get_client_paths(10)

    def test_get_local_user_data(self, sample_data_dir):
        """Test get_local_user_data returns LocalUserData entity."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            local_data = partitioner.get_local_user_data(0)

            assert isinstance(local_data, LocalUserData)
            assert local_data.client_id == '0'
            assert len(local_data.user_ids) > 0
            assert local_data.n_ratings > 0

    def test_load_partition_config(self, sample_data_dir):
        """Test load_partition_config loads saved config."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            config = UserPartitioner.load_partition_config(output_dir)

            assert config['num_clients'] == 5
            assert 'total_users' in config


class TestVerifyPartitions:
    """Tests for verify_partitions function."""

    def test_verify_valid_partitions(self, sample_data_dir):
        """Test verify_partitions returns True for valid partitions."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            result = verify_partitions(output_dir)
            assert result is True

    def test_verify_detects_missing_users(self, sample_data_dir):
        """Test verify_partitions detects when not all users are assigned."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_dir = Path(output_dir)

            partitioner = UserPartitioner(PartitionConfig(num_clients=5))
            partitioner.partition(sample_data_dir, output_dir)

            # Corrupt one client's data by removing a user
            client_train = pd.read_parquet(output_dir / 'client_0' / 'train.parquet')
            corrupted = client_train[client_train['user_idx'] != client_train['user_idx'].iloc[0]]
            corrupted.to_parquet(output_dir / 'client_0' / 'train.parquet', index=False)

            with pytest.raises(ValueError, match="Not all users assigned"):
                verify_partitions(output_dir)
