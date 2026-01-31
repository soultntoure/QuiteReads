"""Lightning DataModule for federated clients.

Loads client-specific partitioned data for federated learning training.
Each client gets its own exclusive set of users while sharing the global
item catalog.
"""

from pathlib import Path
from typing import Optional

import lightning as L
from torch.utils.data import DataLoader

from app.application.data.data_loader_factory import create_eval_loader, create_train_loader
from app.application.data.ratings_dataset import RatingsDataset


class ClientDataModule(L.LightningDataModule):
    """Lightning DataModule for federated client data.

    Loads partitioned train/val data for a specific client from the
    federated partition directory structure.

    Expected directory structure:
        partition_dir/
        ├── partition_config.json
        ├── client_0/
        │   ├── train.parquet
        │   └── val.parquet
        ├── client_1/
        │   ├── train.parquet
        │   └── val.parquet
        ...

    Example:
        >>> datamodule = ClientDataModule(
        ...     client_id=0,
        ...     partition_dir=Path("data/federated"),
        ...     global_n_users=5949,
        ...     global_n_items=2856,
        ...     global_mean=4.02,
        ...     batch_size=1024
        ... )
        >>> datamodule.prepare_data()
        >>> datamodule.setup()
        >>> train_loader = datamodule.train_dataloader()
    """

    def __init__(
        self,
        client_id: int,
        partition_dir: Path | str,
        global_n_users: int,
        global_n_items: int,
        global_mean: Optional[float] = None,
        batch_size: int = 1024,
        num_workers: int = 0,
    ):
        """Initialize ClientDataModule.

        Args:
            client_id: Client index (0 to num_clients-1)
            partition_dir: Directory containing partitioned client data
            global_n_users: Total number of users across all clients
            global_n_items: Total number of items (books)
            global_mean: Global mean rating (optional, computed from train if None)
            batch_size: Batch size for DataLoaders
            num_workers: Number of worker processes for data loading
        """
        super().__init__()
        self.client_id = client_id
        self.partition_dir = Path(partition_dir)
        self.global_n_users = global_n_users
        self.global_n_items = global_n_items
        self._global_mean = global_mean
        self.batch_size = batch_size
        self.num_workers = num_workers

        # Client-specific paths
        self.client_dir = self.partition_dir / f"client_{client_id}"
        self.train_path = self.client_dir / "train.parquet"
        self.val_path = self.client_dir / "val.parquet"

        # Datasets (created in setup)
        self.train_dataset: Optional[RatingsDataset] = None
        self.val_dataset: Optional[RatingsDataset] = None

    @property
    def global_mean(self) -> float:
        """Global mean rating.

        If not provided during initialization, computes from training data.
        """
        if self._global_mean is None:
            if self.train_dataset is not None:
                self._global_mean = self.train_dataset.rating_mean
            else:
                raise RuntimeError(
                    "global_mean not set and train_dataset not initialized. "
                    "Call setup() first or provide global_mean in constructor."
                )
        return self._global_mean

    def prepare_data(self) -> None:
        """Download/prepare data (Lightning interface).

        For federated clients, data is already partitioned, so this
        just validates that the required files exist.
        """
        if not self.client_dir.exists():
            raise FileNotFoundError(
                f"Client directory not found: {self.client_dir}\n"
                f"Run partitioning first."
            )

        if not self.train_path.exists():
            raise FileNotFoundError(
                f"Training data not found: {self.train_path}\n"
                f"Run partitioning first."
            )

        if not self.val_path.exists():
            raise FileNotFoundError(
                f"Validation data not found: {self.val_path}\n"
                f"Run partitioning first."
            )

    def setup(self, stage: Optional[str] = None) -> None:
        """Setup datasets (Lightning interface).

        Args:
            stage: Lightning stage ('fit', 'validate', 'test', or None for all)
        """
        if stage == "fit" or stage is None:
            self.train_dataset = RatingsDataset(
                parquet_path=self.train_path,
                n_users=self.global_n_users,
                n_items=self.global_n_items,
            )

        if stage == "fit" or stage == "validate" or stage is None:
            self.val_dataset = RatingsDataset(
                parquet_path=self.val_path,
                n_users=self.global_n_users,
                n_items=self.global_n_items,
            )

    def train_dataloader(self) -> DataLoader:
        """Create training DataLoader (Lightning interface).

        Returns:
            DataLoader with shuffled training data
        """
        if self.train_dataset is None:
            raise RuntimeError("setup() must be called before train_dataloader()")

        return create_train_loader(
            dataset=self.train_dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            pin_memory=True,
        )

    def val_dataloader(self) -> DataLoader:
        """Create validation DataLoader (Lightning interface).

        Returns:
            DataLoader with validation data (no shuffling)
        """
        if self.val_dataset is None:
            raise RuntimeError("setup() must be called before val_dataloader()")

        return create_eval_loader(
            dataset=self.val_dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            pin_memory=True,
        )

    def get_num_examples(self) -> int:
        """Get number of training examples for this client.

        Returns:
            Number of training interactions

        Raises:
            RuntimeError: If setup() hasn't been called
        """
        if self.train_dataset is None:
            raise RuntimeError("setup() must be called before get_num_examples()")

        return len(self.train_dataset)
