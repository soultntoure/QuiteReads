"""Data partitioning for federated learning.

Partitions Goodreads dataset by user_id for cross-silo federated learning
simulation. Each client receives an exclusive set of users while sharing
the global item catalog.

Adapted from research repo: src/federated/partitioner.py
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.entities import LocalUserData


@dataclass
class PartitionConfig:
    """Configuration for data partitioning.

    Attributes:
        num_clients: Number of federated clients (default: 10)
        seed: Random seed for reproducibility (default: 42)
    """

    num_clients: int = 2
    seed: int = 42


@dataclass
class PartitionResult:
    """Result of partitioning operation.

    Attributes:
        num_clients: Number of clients created
        output_dir: Directory containing partitioned data
        users_per_client: List of user counts per client
        interactions_per_client: Dict mapping client_id to (train, val) counts
        config_path: Path to saved configuration file
        global_n_users: Total unique users
        global_n_items: Total unique items
        global_mean: Global mean rating
    """

    num_clients: int
    output_dir: Path
    users_per_client: List[int]
    interactions_per_client: Dict[int, Tuple[int, int]]
    config_path: Path
    global_n_users: int
    global_n_items: int
    global_mean: float


class UserPartitioner:
    """Partitions rating data by user_id for federated learning.

    Implements IID (Independent and Identically Distributed) partitioning
    where users are randomly shuffled and evenly distributed across clients.
    Each client receives an exclusive set of users.

    Attributes:
        config: Partitioning configuration

    Example:
        >>> partitioner = UserPartitioner(PartitionConfig(num_clients=10))
        >>> result = partitioner.partition(
        ...     data_dir=Path("data"),
        ...     output_dir=Path("data/federated")
        ... )
        >>> print(f"Created {result.num_clients} client partitions")
    """

    def __init__(self, config: Optional[PartitionConfig] = None):
        """Initialize partitioner.

        Args:
            config: Partitioning configuration (uses defaults if None)
        """
        self.config = config or PartitionConfig()
        self._user_to_client: Dict[int, int] = {}
        self._output_dir: Optional[Path] = None

    def partition(self, data_dir: Path, output_dir: Path) -> PartitionResult:
        """Partition train/val data by user_id.

        Reads the preprocessed train and validation parquet files,
        assigns users to clients, and saves per-client data files.

        Args:
            data_dir: Directory containing splits/ folder with train.parquet, val.parquet
            output_dir: Directory to save partitioned data

        Returns:
            PartitionResult with partition statistics

        Raises:
            FileNotFoundError: If train.parquet or val.parquet not found
            ValueError: If num_clients exceeds number of unique users
        """
        data_dir = Path(data_dir)
        output_dir = Path(output_dir)

        # Load data
        train_path = data_dir / "splits" / "train.parquet"
        val_path = data_dir / "splits" / "val.parquet"

        if not train_path.exists():
            raise FileNotFoundError(f"Training data not found: {train_path}")
        if not val_path.exists():
            raise FileNotFoundError(f"Validation data not found: {val_path}")

        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)

        # Get unique users from training data
        unique_users = train_df["user_idx"].unique()
        n_users = len(unique_users)

        if self.config.num_clients > n_users:
            raise ValueError(
                f"num_clients ({self.config.num_clients}) exceeds unique users ({n_users})"
            )

        # Shuffle users with seed for reproducibility
        rng = np.random.default_rng(self.config.seed)
        shuffled_users = rng.permutation(unique_users)

        # Split users into roughly equal chunks
        user_splits = np.array_split(shuffled_users, self.config.num_clients)

        # Create user -> client mapping
        self._user_to_client = {}
        for client_id, users in enumerate(user_splits):
            for user in users:
                self._user_to_client[int(user)] = client_id

        # Clear and recreate output directory for clean state
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir = output_dir

        # Calculate global statistics
        total_items = max(train_df["item_idx"].max(), val_df["item_idx"].max()) + 1
        global_mean = float(train_df["rating"].mean())

        # Partition and save data for each client
        users_per_client: List[int] = []
        interactions_per_client: Dict[int, Tuple[int, int]] = {}

        for client_id in range(self.config.num_clients):
            client_users = user_splits[client_id]
            users_per_client.append(len(client_users))

            # Filter train and val data for this client's users
            client_train = train_df[train_df["user_idx"].isin(client_users)]
            client_val = val_df[val_df["user_idx"].isin(client_users)]

            # Create client directory
            client_dir = output_dir / f"client_{client_id}"
            client_dir.mkdir(parents=True, exist_ok=True)

            # Save parquet files
            client_train.to_parquet(client_dir / "train.parquet", index=False)
            client_val.to_parquet(client_dir / "val.parquet", index=False)

            interactions_per_client[client_id] = (len(client_train), len(client_val))

        # Save partition configuration
        config_dict = {
            "num_clients": self.config.num_clients,
            "seed": self.config.seed,
            "total_users": n_users,
            "total_items": int(total_items),
            "global_mean": global_mean,
            "total_train_interactions": len(train_df),
            "total_val_interactions": len(val_df),
            "users_per_client": users_per_client,
            "interactions_per_client": {
                str(k): {"train": v[0], "val": v[1]}
                for k, v in interactions_per_client.items()
            },
            "user_to_client": {str(k): v for k, v in self._user_to_client.items()},
        }

        config_path = output_dir / "partition_config.json"
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        return PartitionResult(
            num_clients=self.config.num_clients,
            output_dir=output_dir,
            users_per_client=users_per_client,
            interactions_per_client=interactions_per_client,
            config_path=config_path,
            global_n_users=n_users,
            global_n_items=int(total_items),
            global_mean=global_mean,
        )

    def get_client_paths(self, client_id: int) -> Tuple[Path, Path]:
        """Get paths to client's train and val parquet files.

        Args:
            client_id: Client index (0 to num_clients-1)

        Returns:
            Tuple of (train_path, val_path)

        Raises:
            ValueError: If client_id is out of range
            RuntimeError: If partition() hasn't been called
        """
        if self._output_dir is None:
            raise RuntimeError("partition() must be called before get_client_paths()")

        if client_id < 0 or client_id >= self.config.num_clients:
            raise ValueError(
                f"client_id {client_id} out of range [0, {self.config.num_clients})"
            )

        client_dir = self._output_dir / f"client_{client_id}"
        return client_dir / "train.parquet", client_dir / "val.parquet"

    def get_local_user_data(self, client_id: int) -> LocalUserData:
        """Get LocalUserData domain entity for a client.

        Args:
            client_id: Client index (0 to num_clients-1)

        Returns:
            LocalUserData domain entity

        Raises:
            RuntimeError: If partition() hasn't been called
            ValueError: If client_id is out of range
        """
        train_path, val_path = self.get_client_paths(client_id)

        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(val_path)

        # Combine train and val for full client data
        ratings_df = pd.concat([train_df, val_df], ignore_index=True)

        # Get user IDs as strings (domain entity expects string IDs)
        user_ids = [str(uid) for uid in ratings_df["user_idx"].unique()]

        return LocalUserData(
            client_id=str(client_id),
            user_ids=user_ids,
            ratings_df=ratings_df,
        )

    @staticmethod
    def load_partition_config(partition_dir: Path) -> dict:
        """Load partition configuration from JSON file.

        Args:
            partition_dir: Directory containing partition_config.json

        Returns:
            Configuration dictionary
        """
        config_path = partition_dir / "partition_config.json"
        with open(config_path, "r") as f:
            return json.load(f)


def verify_partitions(output_dir: Path) -> bool:
    """Verify partitions are valid (disjoint and complete).

    Args:
        output_dir: Directory containing partitioned data

    Returns:
        True if partitions are valid

    Raises:
        ValueError: If partitions are invalid
    """
    config = UserPartitioner.load_partition_config(output_dir)

    num_clients = config["num_clients"]
    total_users = config["total_users"]

    # Collect all users across partitions
    all_users: set = set()
    user_counts: List[int] = []

    for client_id in range(num_clients):
        client_dir = output_dir / f"client_{client_id}"
        train_df = pd.read_parquet(client_dir / "train.parquet")
        client_users = set(train_df["user_idx"].unique())

        # Check for overlap with previous clients
        overlap = all_users & client_users
        if overlap:
            raise ValueError(
                f"Client {client_id} has overlapping users with other clients: {overlap}"
            )

        all_users.update(client_users)
        user_counts.append(len(client_users))

    # Check all users are assigned
    if len(all_users) != total_users:
        raise ValueError(
            f"Not all users assigned: {len(all_users)} vs {total_users} expected"
        )

    return True
