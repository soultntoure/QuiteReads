# Data Module

## Overview
Provides data loading, preprocessing, and partitioning capabilities for federated book recommendation experiments. Handles the complete pipeline from raw Goodreads JSON to PyTorch-ready tensors and federated client partitions.

> **📊 [Complete Data Flow Guide](DATA_FLOW.md)** - Detailed visual walkthrough of the entire data pipeline from raw JSON to training-ready tensors, including directory structures, file sizes, and transformation statistics.

## Purpose
- Load and preprocess Goodreads rating data (JSON → parquet → PyTorch tensors)
- Filter sparse users/items and create train/val/test splits
- Partition data by user for federated learning simulations
- Create PyTorch DataLoaders with appropriate shuffling/batching
- Provide metadata for model initialization (n_users, n_items, global_mean)

## Module Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `ratings_dataset.py` | PyTorch Dataset for ratings | Loads parquet files as tensors (user_idx, item_idx, rating) |
| `dataset_loader.py` | High-level dataset management | Loads preprocessed data, creates DataLoaders, provides metadata |
| `data_loader_factory.py` | DataLoader factory functions | Creates train (shuffled) and eval (non-shuffled) DataLoaders |
| `preprocessing.py` | Complete preprocessing pipeline | Filters implicit ratings, sparse entities, creates ID mappings and splits |
| `partitioner.py` | Federated data partitioning | IID user-based partitioning for cross-silo FL simulation |

---

## 1. ratings_dataset.py

### Overview
PyTorch Dataset implementation that loads preprocessed parquet files containing (user_idx, item_idx, rating) tuples and provides them as tensors for training.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `RatingsDataset` | PyTorch Dataset for user-item ratings | Loads parquet, converts to tensors, tracks n_users/n_items for embeddings |
| `__init__(parquet_path, n_users, n_items)` | Initialize dataset from parquet | Validates columns (user_idx, item_idx, rating), infers dimensions if not provided |
| `__getitem__(idx)` | Return single interaction | Returns tuple of (user_idx, item_idx, rating) as tensors |
| `rating_mean` property | Mean rating across dataset | Used for global bias initialization |
| `local_users` property | Set of unique user indices | Useful for federated scenarios to identify client users |

### Usage Examples

```python
from app.application.data import RatingsDataset

# Load training dataset
train_dataset = RatingsDataset(
    parquet_path='data/splits/train.parquet',
    n_users=5000,  # Provide for consistency across splits
    n_items=3000
)

# Access dataset properties
print(f"Interactions: {len(train_dataset)}")
print(f"Users: {train_dataset.n_users}, Items: {train_dataset.n_items}")
print(f"Global mean: {train_dataset.rating_mean:.2f}")

# Get single interaction
user_idx, item_idx, rating = train_dataset[0]

# Use with DataLoader
from torch.utils.data import DataLoader
loader = DataLoader(train_dataset, batch_size=1024, shuffle=True)
```

### Significance
- **Single Responsibility**: Dataset only handles data loading and tensor conversion, not DataLoader creation
- **Embedding Dimensions**: Stores `n_users` and `n_items` needed for PyTorch `nn.Embedding` table initialization
- **Federated Support**: `local_users` property enables tracking which users belong to which federated clients
- **Lazy Caching**: `local_users` is computed once and cached for efficiency

---

## 2. dataset_loader.py

### Overview
High-level manager for loading preprocessed Goodreads datasets. Handles metadata loading, ID mappings, dataset creation, and provides model initialization parameters. Acts as the primary interface for accessing data in experiments.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `DatasetMetadata` | Dataclass for dataset statistics | Contains n_users, n_items, global_mean, split sizes, sparsity |
| `DatasetLoader` | Main dataset management class | Loads metadata/mappings, creates RatingsDataset instances, provides DataLoaders |
| `verify_data_exists()` | Check required files exist | Validates metadata.json and train/val/test parquet files before loading |
| `load()` | Load metadata and mappings | Must be called before accessing any data properties |
| `n_users`, `n_items`, `global_mean` | Key model parameters | Properties that extract values from metadata |
| `get_model_init_args()` | Model initialization dictionary | Returns dict that can be unpacked into model constructor |
| `get_train_loader()` | Create training DataLoader | Returns DataLoader with shuffle=True |
| `get_val_loader()`, `get_test_loader()` | Create evaluation DataLoaders | Returns DataLoader with shuffle=False |
| `get_domain_dataset()` | Get domain Dataset entity | Returns domain entity with DataFrame and mappings for higher-level operations |

### Usage Examples

```python
from app.application.data import DatasetLoader
from pathlib import Path

# Initialize and load
loader = DatasetLoader(data_dir=Path('data'))
loader.load()

# Get model initialization parameters
print(f"Users: {loader.n_users}, Items: {loader.n_items}")
print(f"Global mean: {loader.global_mean:.2f}")

# Initialize model with unpacked args
from src.models.matrix_factorization import BiasedMatrixFactorization
model = BiasedMatrixFactorization(
    **loader.get_model_init_args(),
    n_factors=50,
    learning_rate=0.01
)

# Get DataLoaders for training
train_loader = loader.get_train_loader(batch_size=1024)
val_loader = loader.get_val_loader(batch_size=1024)

# Access metadata
metadata = loader.get_metadata()
print(f"Sparsity: {metadata.sparsity:.4f}")
print(f"Train size: {metadata.train_size:,}")

# Get domain entity for higher-level operations
domain_dataset = loader.get_domain_dataset()
```

### Significance
- **Facade Pattern**: Provides simple interface to complex data loading operations
- **Lazy Loading**: Datasets are created only when first accessed, saving memory
- **State Validation**: `_ensure_loaded()` enforces that `load()` is called before data access
- **Separation of Concerns**: Handles file I/O and metadata parsing, delegates tensor operations to RatingsDataset
- **Domain Bridge**: `get_domain_dataset()` returns domain entities for use in higher application layers

---

## 3. data_loader_factory.py

### Overview
Factory functions for creating PyTorch DataLoaders from RatingsDataset instances. Encapsulates the difference between training (shuffled) and evaluation (non-shuffled) DataLoader configurations.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `create_train_loader()` | Create training DataLoader | shuffle=True, drop_last=False, configurable batch_size/workers |
| `create_eval_loader()` | Create evaluation DataLoader | shuffle=False, drop_last=False, configurable batch_size/workers |

### Usage Examples

```python
from app.application.data import RatingsDataset, create_train_loader, create_eval_loader

# Create datasets
train_ds = RatingsDataset('data/splits/train.parquet')
val_ds = RatingsDataset('data/splits/val.parquet')

# Create DataLoaders
train_loader = create_train_loader(
    dataset=train_ds,
    batch_size=1024,
    num_workers=4,
    pin_memory=True  # Faster GPU transfer
)

val_loader = create_eval_loader(
    dataset=val_ds,
    batch_size=2048,  # Larger batch for eval since no gradients
    num_workers=4,
    pin_memory=True
)

# Use in training loop
for batch_idx, (users, items, ratings) in enumerate(train_loader):
    # Training logic
    pass
```

### Significance
- **Factory Pattern**: Centralizes DataLoader creation logic with sensible defaults
- **Single Responsibility**: Each function creates one type of DataLoader (train vs eval)
- **Consistency**: Ensures all DataLoaders use consistent configuration (drop_last=False)
- **Deterministic Evaluation**: Evaluation DataLoaders never shuffle, ensuring reproducible metrics

---

## 4. preprocessing.py

### Overview
Complete data preprocessing pipeline for the Goodreads Poetry Books dataset. Implements filtering, ID mapping, train/val/test splitting, and artifact saving. Designed for the IEEE conference paper on federated book recommendation systems.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `PreprocessingConfig` | Configuration dataclass | min_user_ratings=20, min_item_ratings=20, val_ratio=0.1, test_ratio=0.2, seed=42 |
| `load_raw_interactions()` | Load JSON Lines data | Parses Goodreads format (one JSON object per line) |
| `filter_implicit_interactions()` | Remove rating=0 | Goodreads uses rating=0 for "added to shelf" (not actual rating) |
| `iterative_filter()` | Iteratively filter sparse entities | Removes users/items below threshold until convergence |
| `create_id_mappings()` | Create bidirectional ID maps | Maps string IDs to contiguous integers for PyTorch embeddings |
| `apply_id_mappings()` | Apply mappings to DataFrame | Converts user_id/book_id to user_idx/item_idx |
| `create_train_val_test_split()` | Random 70/10/20 split | Stratified by nothing (pure random) for simplicity |
| `compute_statistics()` | Calculate dataset statistics | Sparsity, retention rate, rating distribution |
| `save_artifacts()` | Save all outputs | Saves parquet files, JSON mappings, metadata |
| `run_preprocessing_pipeline()` | Execute full pipeline | Orchestrates all steps and returns metadata |

### Usage Examples

```python
from pathlib import Path
from app.application.data import PreprocessingConfig, run_preprocessing_pipeline

# Run with default config (20 min ratings, 70/10/20 split)
metadata = run_preprocessing_pipeline(
    raw_path=Path('data/raw/goodreads_interactions_poetry.json'),
    output_dir=Path('data')
)

print(f"Filtered users: {metadata['statistics']['filtered_users']:,}")
print(f"Sparsity: {metadata['statistics']['sparsity_percent']}")

# Run with custom config
custom_config = PreprocessingConfig(
    min_user_ratings=10,  # Lower threshold
    min_item_ratings=10,
    val_ratio=0.15,
    test_ratio=0.15,
    random_seed=123
)

metadata = run_preprocessing_pipeline(
    raw_path=Path('data/raw/goodreads_interactions_poetry.json'),
    output_dir=Path('data'),
    config=custom_config
)
```

**CLI Usage:**
```bash
# Default preprocessing
uv run python -m app.application.data.preprocessing \
    --raw-path data/raw/goodreads_interactions_poetry.json

# Custom thresholds
uv run python -m app.application.data.preprocessing \
    --raw-path data/raw/goodreads_interactions_poetry.json \
    --min-user-ratings 10 \
    --min-item-ratings 10 \
    --val-ratio 0.15 \
    --test-ratio 0.15 \
    --seed 123
```

### Significance
- **Goodreads Policy Alignment**: 20-rating threshold matches Goodreads' recommendation requirements
- **Iterative Filtering**: Handles cascading sparsity (removing users may make items sparse)
- **Convergence Guarantee**: Iterative filtering converges when no more entities fall below threshold
- **Reproducibility**: Seeds all random operations, saves full metadata for experiment tracking
- **PyTorch Compatibility**: Creates contiguous integer IDs required by `nn.Embedding`
- **CLI + Programmatic**: Usable both as script and imported function

---

## 5. partitioner.py

### Overview
Implements IID (Independent and Identically Distributed) user-based partitioning for federated learning simulation. Assigns users to clients in a privacy-preserving manner where each client receives an exclusive set of users.

### Components

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `PartitionConfig` | Partitioning configuration | num_clients=10, seed=42 |
| `PartitionResult` | Dataclass for partition stats | Contains client counts, interactions, paths, global parameters |
| `UserPartitioner` | Main partitioning class | IID random assignment of users to clients |
| `partition()` | Execute partitioning | Shuffles users, splits into chunks, saves per-client parquet files |
| `get_client_paths()` | Get client's train/val paths | Returns tuple of (train_path, val_path) for a client |
| `get_local_user_data()` | Get domain entity for client | Returns LocalUserData with client's users and ratings |
| `verify_partitions()` | Validate partition correctness | Checks users are disjoint and complete |

### Usage Examples

```python
from pathlib import Path
from app.application.data import UserPartitioner, PartitionConfig, verify_partitions

# Create partitioner
config = PartitionConfig(num_clients=10, seed=42)
partitioner = UserPartitioner(config)

# Partition data
result = partitioner.partition(
    data_dir=Path('data'),
    output_dir=Path('data/federated')
)

print(f"Created {result.num_clients} clients")
print(f"Users per client: {result.users_per_client}")
print(f"Global mean: {result.global_mean:.2f}")

# Access client data
train_path, val_path = partitioner.get_client_paths(client_id=0)
print(f"Client 0 train: {train_path}")

# Get domain entity for federated training
local_data = partitioner.get_local_user_data(client_id=0)
print(f"Client 0 has {len(local_data.user_ids)} users")

# Verify partitions are correct
is_valid = verify_partitions(Path('data/federated'))
print(f"Partitions valid: {is_valid}")
```

**Output Structure:**
```
data/federated/
├── partition_config.json  # Metadata and mappings
├── client_0/
│   ├── train.parquet
│   └── val.parquet
├── client_1/
│   ├── train.parquet
│   └── val.parquet
...
└── client_9/
    ├── train.parquet
    └── val.parquet
```

### Significance
- **IID Partitioning**: Users randomly shuffled and evenly distributed (baseline for FL experiments)
- **Privacy Preservation**: Each client gets exclusive users (no user data shared across clients)
- **Disjoint Partitions**: `verify_partitions()` ensures no user appears in multiple clients
- **Global Item Catalog**: All clients share the same item space (books are public)
- **Reproducibility**: Seeded shuffling ensures consistent partitions across runs
- **Domain Bridge**: `get_local_user_data()` returns domain entities for use in federated simulation

---

## Module Significance

| Aspect | Value |
|--------|-------|
| **Architectural Layer** | Application layer (orchestrates domain entities, wraps infrastructure) |
| **Design Pattern** | Repository pattern (data access), Factory pattern (DataLoader creation), Facade pattern (DatasetLoader) |
| **Dependencies** | Depends on `app.core.entities` (Dataset, LocalUserData), independent of infrastructure and API layers |
| **Consumed By** | `app.application.training` (trainers need DataLoaders), `app.application.services` (experiment services need data) |
| **Key Principle** | **SOLID**: Single Responsibility (each file has one job), Dependency Inversion (returns domain entities, not DataFrames) |
| **Testability** | Highly testable (pure functions, deterministic with seeds, no database dependencies) |
| **Federated Learning** | Supports both centralized (DatasetLoader) and federated (UserPartitioner) scenarios |
| **Preprocessing Origin** | Adapted from research repo's `src/data/` pipeline, integrated with clean architecture |
| **PyTorch Integration** | Provides native PyTorch Dataset and DataLoader, replacing Lightning DataModule |
