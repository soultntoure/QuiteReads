"""Dataset loading and management.

Loads preprocessed Goodreads data from parquet files and metadata.
Provides high-level interface for accessing training data and model
initialization parameters.

Adapted from research repo: src/data/datamodule.py (RatingsDataModule)
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from torch.utils.data import DataLoader

from app.application.data.data_loader_factory import create_eval_loader, create_train_loader
from app.application.data.ratings_dataset import RatingsDataset
from app.core.entities import Dataset


@dataclass
class DatasetMetadata:
    """Metadata about a loaded dataset.

    Contains information needed for model initialization and training.
    """

    n_users: int
    n_items: int
    global_mean: float
    train_size: int
    val_size: int
    test_size: int
    sparsity: float


class DatasetLoader:
    """Loads and manages preprocessed Goodreads dataset.

    This class handles:
    - Loading preprocessed parquet files for train/val/test splits
    - Loading metadata and ID mappings
    - Creating RatingsDataset and DataLoader instances
    - Providing model initialization parameters

    Expected directory structure:
        data_dir/
        ├── processed/
        │   ├── metadata.json
        │   ├── user_mapping.json
        │   └── item_mapping.json
        └── splits/
            ├── train.parquet
            ├── val.parquet
            └── test.parquet

    Example:
        >>> loader = DatasetLoader(data_dir='data')
        >>> loader.load()
        >>> print(f"Users: {loader.n_users}, Items: {loader.n_items}")
        >>> train_loader = loader.get_train_loader(batch_size=1024)
    """

    def __init__(self, data_dir: str | Path):
        """Initialize DatasetLoader.

        Args:
            data_dir: Base directory containing 'processed/' and 'splits/' folders
        """
        self.data_dir = Path(data_dir)

        # Paths
        self._processed_dir = self.data_dir / 'processed'
        self._splits_dir = self.data_dir / 'splits'

        # Loaded state
        self._metadata: Optional[dict] = None
        self._user_mapping: Optional[Dict[str, int]] = None
        self._item_mapping: Optional[Dict[str, int]] = None

        # Datasets (lazy loaded)
        self._train_dataset: Optional[RatingsDataset] = None
        self._val_dataset: Optional[RatingsDataset] = None
        self._test_dataset: Optional[RatingsDataset] = None

        # Computed values
        self._global_mean: Optional[float] = None

    def verify_data_exists(self) -> None:
        """Verify all required data files exist.

        Raises:
            FileNotFoundError: If any required file is missing
        """
        metadata_path = self._processed_dir / 'metadata.json'
        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {metadata_path}\n"
                "Run preprocessing first."
            )

        for split in ['train', 'val', 'test']:
            split_path = self._splits_dir / f'{split}.parquet'
            if not split_path.exists():
                raise FileNotFoundError(
                    f"Split file not found: {split_path}\n"
                    "Run preprocessing first."
                )

    def load(self) -> None:
        """Load metadata and mappings.

        Must be called before accessing data or creating DataLoaders.

        Raises:
            FileNotFoundError: If required files don't exist
        """
        self.verify_data_exists()

        # Load metadata
        with open(self._processed_dir / 'metadata.json', 'r') as f:
            self._metadata = json.load(f)

        # Load ID mappings
        with open(self._processed_dir / 'user_mapping.json', 'r') as f:
            self._user_mapping = json.load(f)

        with open(self._processed_dir / 'item_mapping.json', 'r') as f:
            self._item_mapping = json.load(f)

    @property
    def n_users(self) -> int:
        """Total number of unique users."""
        self._ensure_loaded()
        assert self._metadata is not None
        return self._metadata['statistics']['filtered_users']

    @property
    def n_items(self) -> int:
        """Total number of unique items."""
        self._ensure_loaded()
        assert self._metadata is not None
        return self._metadata['statistics']['filtered_items']

    @property
    def global_mean(self) -> float:
        """Global mean rating from training set.

        Computed lazily from training data for accuracy.
        """
        if self._global_mean is None:
            train_dataset = self._get_train_dataset()
            self._global_mean = train_dataset.rating_mean
        assert self._global_mean is not None
        return self._global_mean

    @property
    def user_mapping(self) -> Dict[str, int]:
        """Mapping from original user_id to integer index."""
        self._ensure_loaded()
        assert self._user_mapping is not None
        return self._user_mapping

    @property
    def item_mapping(self) -> Dict[str, int]:
        """Mapping from original item_id (book_id) to integer index."""
        self._ensure_loaded()
        assert self._item_mapping is not None
        return self._item_mapping

    def get_metadata(self) -> DatasetMetadata:
        """Get comprehensive dataset metadata.

        Returns:
            DatasetMetadata with all relevant statistics
        """
        self._ensure_loaded()
        assert self._metadata is not None
        stats = self._metadata['statistics']

        return DatasetMetadata(
            n_users=stats['filtered_users'],
            n_items=stats['filtered_items'],
            global_mean=self.global_mean,
            train_size=self._metadata['train_size'],
            val_size=self._metadata['val_size'],
            test_size=self._metadata['test_size'],
            sparsity=stats['sparsity'],
        )

    def get_model_init_args(self) -> dict:
        """Get arguments needed for model initialization.

        Returns dictionary with n_users, n_items, and global_mean
        that can be unpacked into the model constructor.

        Returns:
            Dictionary with model initialization arguments

        Example:
            >>> loader = DatasetLoader('data')
            >>> loader.load()
            >>> model = BiasedMatrixFactorization(
            ...     **loader.get_model_init_args(),
            ...     n_factors=50
            ... )
        """
        return {
            'n_users': self.n_users,
            'n_items': self.n_items,
            'global_mean': self.global_mean,
        }

    def get_domain_dataset(self) -> Dataset:
        """Get domain Dataset entity.

        Returns the domain-level Dataset with DataFrame and mappings.
        Useful for higher-level operations that need raw data access.

        Returns:
            Dataset domain entity
        """
        self._ensure_loaded()

        # Load full indexed interactions
        df = pd.read_parquet(self._processed_dir / 'interactions_indexed.parquet')

        return Dataset(
            df=df,
            user_mapping=self._user_mapping,
            book_mapping=self._item_mapping,
            sparse_matrix=None,  # Can be computed if needed
        )

    def get_train_loader(
        self,
        batch_size: int = 1024,
        num_workers: int = 0,
        pin_memory: bool = True,
    ) -> DataLoader:
        """Create DataLoader for training data.

        Args:
            batch_size: Number of samples per batch
            num_workers: Number of data loading workers
            pin_memory: Pin memory for GPU transfer

        Returns:
            DataLoader with shuffled training data
        """
        dataset = self._get_train_dataset()
        return create_train_loader(
            dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )

    def get_val_loader(
        self,
        batch_size: int = 1024,
        num_workers: int = 0,
        pin_memory: bool = True,
    ) -> DataLoader:
        """Create DataLoader for validation data.

        Args:
            batch_size: Number of samples per batch
            num_workers: Number of data loading workers
            pin_memory: Pin memory for GPU transfer

        Returns:
            DataLoader with validation data (no shuffling)
        """
        dataset = self._get_val_dataset()
        return create_eval_loader(
            dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )

    def get_test_loader(
        self,
        batch_size: int = 1024,
        num_workers: int = 0,
        pin_memory: bool = True,
    ) -> DataLoader:
        """Create DataLoader for test data.

        Args:
            batch_size: Number of samples per batch
            num_workers: Number of data loading workers
            pin_memory: Pin memory for GPU transfer

        Returns:
            DataLoader with test data (no shuffling)
        """
        dataset = self._get_test_dataset()
        return create_eval_loader(
            dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            pin_memory=pin_memory,
        )

    def get_train_dataset(self) -> RatingsDataset:
        """Get training RatingsDataset directly.

        Returns:
            RatingsDataset for training data
        """
        return self._get_train_dataset()

    def get_val_dataset(self) -> RatingsDataset:
        """Get validation RatingsDataset directly.

        Returns:
            RatingsDataset for validation data
        """
        return self._get_val_dataset()

    def get_test_dataset(self) -> RatingsDataset:
        """Get test RatingsDataset directly.

        Returns:
            RatingsDataset for test data
        """
        return self._get_test_dataset()

    def _ensure_loaded(self) -> None:
        """Ensure metadata has been loaded."""
        if self._metadata is None:
            raise RuntimeError("load() must be called before accessing data")

    def _get_train_dataset(self) -> RatingsDataset:
        """Get or create training dataset."""
        self._ensure_loaded()
        if self._train_dataset is None:
            self._train_dataset = RatingsDataset(
                self._splits_dir / 'train.parquet',
                n_users=self.n_users,
                n_items=self.n_items,
            )
        return self._train_dataset

    def _get_val_dataset(self) -> RatingsDataset:
        """Get or create validation dataset."""
        self._ensure_loaded()
        if self._val_dataset is None:
            self._val_dataset = RatingsDataset(
                self._splits_dir / 'val.parquet',
                n_users=self.n_users,
                n_items=self.n_items,
            )
        return self._val_dataset

    def _get_test_dataset(self) -> RatingsDataset:
        """Get or create test dataset."""
        self._ensure_loaded()
        if self._test_dataset is None:
            self._test_dataset = RatingsDataset(
                self._splits_dir / 'test.parquet',
                n_users=self.n_users,
                n_items=self.n_items,
            )
        return self._test_dataset
