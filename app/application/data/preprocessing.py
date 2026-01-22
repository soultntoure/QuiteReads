"""
Preprocessing Pipeline for Federated Book Recommendation Experiments
=====================================================================

This script implements the data preprocessing pipeline for the IEEE conference paper:
"A Dashboard for Evaluating Federated Learning in Book Recommender Systems"

Dataset: Goodreads Poetry Books Subset
Output: Filtered interactions, ID mappings, train/test splits

Preprocessing Steps:
1. Load raw JSON interactions
2. Select relevant columns (user_id, book_id, rating)
3. Filter implicit interactions (rating == 0)
4. Iteratively filter sparse users and items (min_ratings threshold)
5. Create contiguous ID mappings for PyTorch embeddings
6. Create train/test split
7. Save all artifacts with metadata for reproducibility

Usage:
    python -m app.application.data.preprocessing --raw-path data/raw/goodreads_interactions_poetry.json
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class PreprocessingConfig:
    """Configuration for preprocessing pipeline.

    Attributes:
        min_user_ratings: Minimum ratings required per user (default: 20)
            Justification: Follows Goodreads' policy requiring 20 ratings
            before providing personalized recommendations.
        min_item_ratings: Minimum ratings required per item (default: 20)
            Justification: Symmetric threshold with users for methodological
            consistency and sufficient signal for embedding learning.
        test_ratio: Fraction of interactions for test set (default: 0.2)
        random_seed: Seed for reproducibility (default: 42)
    """
    min_user_ratings: int = 20
    min_item_ratings: int = 20
    val_ratio: float = 0.1
    test_ratio: float = 0.2
    random_seed: int = 42


# =============================================================================
# Data Loading
# =============================================================================

def load_raw_interactions(path: Path) -> pd.DataFrame:
    """Load raw Goodreads interactions from JSON Lines file.

    The Goodreads dataset is stored as JSON Lines (one JSON object per line),
    not as a standard JSON array. This function handles that format.

    Args:
        path: Path to the raw JSON file

    Returns:
        DataFrame with columns: user_id, book_id, rating

    Raises:
        FileNotFoundError: If the raw data file doesn't exist
        ValueError: If required columns are missing
    """
    logger.info(f"Loading raw data from {path}")

    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")

    # Load JSON Lines format
    interactions = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            interactions.append(json.loads(line.strip()))

    df = pd.DataFrame(interactions)
    logger.info(f"Loaded {len(df):,} raw interactions")

    # Validate required columns exist
    required_cols = {'user_id', 'book_id', 'rating'}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # Select only relevant columns for Matrix Factorization
    df = df[['user_id', 'book_id', 'rating']].copy()

    # Ensure rating is numeric
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

    # Drop rows with non-numeric ratings
    nan_count = df['rating'].isna().sum()
    if nan_count > 0:
        logger.warning(f"Found {nan_count} non-numeric ratings, dropping")
        df = df.dropna(subset=['rating'])

    return df


# =============================================================================
# Filtering Functions
# =============================================================================

def filter_implicit_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """Remove implicit interactions (rating == 0).

    In Goodreads, rating=0 means the user added the book to their shelf
    but never actually rated it. These are not valid explicit ratings
    and must be excluded for rating prediction tasks.

    Args:
        df: DataFrame with rating column

    Returns:
        DataFrame with only explicit ratings (1-5)
    """
    n_before = len(df)
    df_filtered = df[df['rating'] > 0].copy()
    n_after = len(df_filtered)

    logger.info(
        f"Filtered implicit ratings: {n_before:,} → {n_after:,} "
        f"({n_before - n_after:,} removed, {100 * n_after / n_before:.1f}% retained)"
    )

    return df_filtered


def filter_sparse_users(df: pd.DataFrame, min_ratings: int) -> pd.DataFrame:
    """Remove users with fewer than min_ratings interactions.

    Users with very few ratings don't provide enough signal to learn
    meaningful latent factor representations. Following Goodreads' own
    policy, we require a minimum number of ratings.

    Args:
        df: DataFrame with user_id column
        min_ratings: Minimum number of ratings required

    Returns:
        DataFrame with only sufficiently active users
    """
    user_counts = df.groupby('user_id').size()
    valid_users = user_counts[user_counts >= min_ratings].index

    return df[df['user_id'].isin(valid_users)].copy()


def filter_sparse_items(df: pd.DataFrame, min_ratings: int) -> pd.DataFrame:
    """Remove items with fewer than min_ratings interactions.

    Items (books) with very few ratings suffer from cold-start problems
    and don't provide enough signal for embedding learning.

    Args:
        df: DataFrame with book_id column
        min_ratings: Minimum number of ratings required

    Returns:
        DataFrame with only sufficiently rated items
    """
    item_counts = df.groupby('book_id').size()
    valid_items = item_counts[item_counts >= min_ratings].index

    return df[df['book_id'].isin(valid_items)].copy()


def iterative_filter(
    df: pd.DataFrame,
    min_user_ratings: int,
    min_item_ratings: int,
    max_iterations: int = 20
) -> Tuple[pd.DataFrame, int]:
    """Iteratively filter users and items until convergence.

    Filtering is iterative because:
    - Removing sparse users may cause some items to become sparse
    - Removing sparse items may cause some users to become sparse
    - This cascade continues until no more entities need removal

    Args:
        df: DataFrame with user_id, book_id columns
        min_user_ratings: Minimum ratings per user
        min_item_ratings: Minimum ratings per item
        max_iterations: Safety limit to prevent infinite loops

    Returns:
        Tuple of (filtered DataFrame, number of iterations)
    """
    logger.info(
        f"Starting iterative filtering (min_user={min_user_ratings}, "
        f"min_item={min_item_ratings})"
    )

    df_filtered = df.copy()
    prev_len = 0
    iteration = 0

    while len(df_filtered) != prev_len and iteration < max_iterations:
        prev_len = len(df_filtered)
        iteration += 1

        # Filter users, then items
        df_filtered = filter_sparse_users(df_filtered, min_user_ratings)
        df_filtered = filter_sparse_items(df_filtered, min_item_ratings)

        n_users = df_filtered['user_id'].nunique()
        n_items = df_filtered['book_id'].nunique()

        logger.info(
            f"  Iteration {iteration}: {len(df_filtered):,} interactions, "
            f"{n_users:,} users, {n_items:,} items"
        )

    logger.info(f"Converged after {iteration} iterations")

    return df_filtered, iteration


# =============================================================================
# ID Mapping Functions
# =============================================================================

def create_id_mappings(
    df: pd.DataFrame
) -> Tuple[dict, dict, dict, dict]:
    """Create bidirectional mappings from original IDs to contiguous integers.

    PyTorch's nn.Embedding requires contiguous integer indices starting from 0.
    We create mappings to convert string IDs to integers and back.

    Args:
        df: DataFrame with user_id and book_id columns

    Returns:
        Tuple of (user_to_idx, idx_to_user, item_to_idx, idx_to_item)
    """
    # Get unique IDs (sorted for reproducibility)
    unique_users = sorted(df['user_id'].unique())
    unique_items = sorted(df['book_id'].unique())

    # Create mappings
    user_to_idx = {user: idx for idx, user in enumerate(unique_users)}
    idx_to_user = {idx: user for user, idx in user_to_idx.items()}

    item_to_idx = {item: idx for idx, item in enumerate(unique_items)}
    idx_to_item = {idx: item for item, idx in item_to_idx.items()}

    logger.info(
        f"Created ID mappings: {len(user_to_idx):,} users, "
        f"{len(item_to_idx):,} items"
    )

    return user_to_idx, idx_to_user, item_to_idx, idx_to_item


def apply_id_mappings(
    df: pd.DataFrame,
    user_to_idx: dict,
    item_to_idx: dict
) -> pd.DataFrame:
    """Apply ID mappings to create indexed DataFrame.

    Args:
        df: DataFrame with original user_id and book_id
        user_to_idx: Mapping from user_id to integer index
        item_to_idx: Mapping from book_id to integer index

    Returns:
        DataFrame with user_idx, item_idx, rating columns
    """
    df_indexed = pd.DataFrame({
        'user_idx': df['user_id'].map(user_to_idx),
        'item_idx': df['book_id'].map(item_to_idx),
        'rating': df['rating'].values
    })

    return df_indexed


# =============================================================================
# Train/Test Split
# =============================================================================

def create_train_val_test_split(
    df: pd.DataFrame,
    val_ratio: float = 0.1,
    test_ratio: float = 0.2,
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create train/validation/test split by randomly sampling interactions.

    Split ratios:
        - Train: 1 - val_ratio - test_ratio (default 70%)
        - Validation: val_ratio (default 10%) - for early stopping, hyperparam tuning
        - Test: test_ratio (default 20%) - final evaluation only

    Args:
        df: DataFrame with interactions
        val_ratio: Fraction of data for validation set
        test_ratio: Fraction of data for test set
        seed: Random seed for reproducibility

    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    np.random.seed(seed)

    n_samples = len(df)
    indices = np.random.permutation(n_samples)

    n_test = int(n_samples * test_ratio)
    n_val = int(n_samples * val_ratio)

    test_indices = indices[:n_test]
    val_indices = indices[n_test:n_test + n_val]
    train_indices = indices[n_test + n_val:]

    train_df = df.iloc[train_indices].reset_index(drop=True)
    val_df = df.iloc[val_indices].reset_index(drop=True)
    test_df = df.iloc[test_indices].reset_index(drop=True)

    logger.info(
        f"Train/val/test split: {len(train_df):,} train, {len(val_df):,} val, "
        f"{len(test_df):,} test ({100*(1-val_ratio-test_ratio):.0f}%/{100*val_ratio:.0f}%/{100*test_ratio:.0f}%)"
    )

    return train_df, val_df, test_df


# =============================================================================
# Metadata and Saving
# =============================================================================

def compute_statistics(df: pd.DataFrame, df_original: pd.DataFrame) -> dict:
    """Compute dataset statistics for metadata.

    Args:
        df: Filtered DataFrame
        df_original: Original DataFrame (before filtering)

    Returns:
        Dictionary of statistics
    """
    n_users = df['user_id'].nunique()
    n_items = df['book_id'].nunique()
    n_interactions = len(df)

    # Sparsity = 1 - (observed / possible)
    sparsity = 1 - (n_interactions / (n_users * n_items))

    stats = {
        'original_interactions': len(df_original),
        'original_users': df_original['user_id'].nunique(),
        'original_items': df_original['book_id'].nunique(),
        'filtered_interactions': n_interactions,
        'filtered_users': n_users,
        'filtered_items': n_items,
        'sparsity': round(sparsity, 6),
        'sparsity_percent': f"{sparsity * 100:.2f}%",
        'density_percent': f"{(1 - sparsity) * 100:.4f}%",
        'rating_mean': round(df['rating'].mean(), 4),
        'rating_std': round(df['rating'].std(), 4),
        'rating_min': int(df['rating'].min()),
        'rating_max': int(df['rating'].max()),
        'retention_rate': f"{100 * n_interactions / len(df_original):.2f}%"
    }

    return stats


def validate_dataset(df: pd.DataFrame, min_users: int = 100, min_items: int = 100):
    """Basic sanity check before saving."""
    n_users = df['user_id'].nunique()
    n_items = df['book_id'].nunique()

    if n_users < min_users:
        raise ValueError(f"Too few users after filtering: {n_users} (min: {min_users})")
    if n_items < min_items:
        raise ValueError(f"Too few items after filtering: {n_items} (min: {min_items})")
    if len(df) < 1000:
        raise ValueError(f"Too few interactions: {len(df)}")

    logger.info("Dataset validation passed ✓")


def save_artifacts(
    df_filtered: pd.DataFrame,
    df_indexed: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    user_to_idx: dict,
    item_to_idx: dict,
    config: PreprocessingConfig,
    stats: dict,
    n_iterations: int,
    output_dir: Path
) -> None:
    """Save all preprocessing artifacts to disk.

    Output structure:
        output_dir/
        ├── processed/
        │   ├── interactions_filtered.parquet  (original IDs)
        │   ├── interactions_indexed.parquet   (integer IDs for PyTorch)
        │   ├── user_mapping.json
        │   ├── item_mapping.json
        │   └── metadata.json
        └── splits/
            ├── train.parquet
            ├── val.parquet
            └── test.parquet

    Args:
        df_filtered: Filtered DataFrame with original IDs
        df_indexed: DataFrame with integer indices
        train_df: Training split
        val_df: Validation split
        test_df: Test split
        user_to_idx: User ID mapping
        item_to_idx: Item ID mapping
        config: Preprocessing configuration
        stats: Dataset statistics
        n_iterations: Number of filtering iterations
        output_dir: Base output directory
    """
    processed_dir = output_dir / 'processed'
    splits_dir = output_dir / 'splits'

    processed_dir.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)

    # Save filtered interactions (both versions)
    df_filtered.to_parquet(processed_dir / 'interactions_filtered.parquet', index=False)
    df_indexed.to_parquet(processed_dir / 'interactions_indexed.parquet', index=False)
    logger.info(f"Saved interactions to {processed_dir}")


    # Save ID mappings
    with open(processed_dir / 'user_mapping.json', 'w') as f:
        json.dump(user_to_idx, f)

    with open(processed_dir / 'item_mapping.json', 'w') as f:
        json.dump(item_to_idx, f)
    logger.info("Saved ID mappings")

    # Save train/val/test splits
    train_df.to_parquet(splits_dir / 'train.parquet', index=False)
    val_df.to_parquet(splits_dir / 'val.parquet', index=False)
    test_df.to_parquet(splits_dir / 'test.parquet', index=False)
    logger.info(f"Saved train/val/test splits to {splits_dir}")

    # Create comprehensive metadata
    metadata = {
        'preprocessing_date': datetime.now().isoformat(),
        'config': asdict(config),
        'filter_iterations': n_iterations,
        'statistics': stats,
        'train_size': len(train_df),
        'val_size': len(val_df),
        'test_size': len(test_df),
        'files': {
            'interactions_filtered': 'processed/interactions_filtered.parquet',
            'interactions_indexed': 'processed/interactions_indexed.parquet',
            'user_mapping': 'processed/user_mapping.json',
            'item_mapping': 'processed/item_mapping.json',
            'train': 'splits/train.parquet',
            'val': 'splits/val.parquet',
            'test': 'splits/test.parquet'
        }
    }

    with open(processed_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved metadata.json")


# =============================================================================
# Main Pipeline
# =============================================================================

def run_preprocessing_pipeline(
    raw_path: Path,
    output_dir: Path,
    config: PreprocessingConfig = None
) -> dict:
    """Execute the full preprocessing pipeline.

    Args:
        raw_path: Path to raw JSON data
        output_dir: Base directory for outputs
        config: Preprocessing configuration (uses defaults if None)

    Returns:
        Dictionary containing metadata and statistics
    """
    if config is None:
        config = PreprocessingConfig()

    logger.info("=" * 60)
    logger.info("PREPROCESSING PIPELINE START")
    logger.info("=" * 60)

    # Step 1: Load raw data
    df_original = load_raw_interactions(raw_path)

    # Step 2: Filter implicit interactions (rating == 0)
    df = filter_implicit_interactions(df_original)

    # Step 3: Iterative filtering of sparse users and items
    df_filtered, n_iterations = iterative_filter(
        df,
        min_user_ratings=config.min_user_ratings,
        min_item_ratings=config.min_item_ratings
    )

    # Step 4: Create ID mappings
    user_to_idx, idx_to_user, item_to_idx, idx_to_item = create_id_mappings(df_filtered)

    # Step 5: Apply mappings to create indexed DataFrame
    df_indexed = apply_id_mappings(df_filtered, user_to_idx, item_to_idx)

    # Step 6: Create train/val/test split
    train_df, val_df, test_df = create_train_val_test_split(
        df_indexed,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio,
        seed=config.random_seed
    )

    # Step 7: Compute statistics
    stats = compute_statistics(df_filtered, df_original)
    validate_dataset(df_filtered)

    # Step 8: Save all artifacts
    save_artifacts(
        df_filtered=df_filtered,
        df_indexed=df_indexed,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        config=config,
        stats=stats,
        n_iterations=n_iterations,
        output_dir=output_dir
    )

    # Final summary
    logger.info("=" * 60)
    logger.info("PREPROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Final dataset: {stats['filtered_interactions']:,} interactions")
    logger.info(f"Users: {stats['filtered_users']:,}")
    logger.info(f"Items: {stats['filtered_items']:,}")
    logger.info(f"Sparsity: {stats['sparsity_percent']}")
    logger.info(f"Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    return {
        'config': asdict(config),
        'statistics': stats,
        'n_iterations': n_iterations
    }


# =============================================================================
# CLI Entry Point
# =============================================================================


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Preprocess Goodreads data for federated recommendation experiments'
    )
    parser.add_argument(
        '--raw-path',
        type=Path,
        default=Path('data/raw/goodreads_interactions_poetry.json'),
        help='Path to raw JSON data'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data'),
        help='Output directory for processed data'
    )
    parser.add_argument(
        '--min-user-ratings',
        type=int,
        default=20,
        help='Minimum ratings per user (default: 20)'
    )
    parser.add_argument(
        '--min-item-ratings',
        type=int,
        default=20,
        help='Minimum ratings per item (default: 20)'
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.1,
        help='Validation set ratio (default: 0.1)'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.2,
        help='Test set ratio (default: 0.2)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed (default: 42)'
    )

    args = parser.parse_args()

    config = PreprocessingConfig(
        min_user_ratings=args.min_user_ratings,
        min_item_ratings=args.min_item_ratings,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.seed
    )

    run_preprocessing_pipeline(
        raw_path=args.raw_path,
        output_dir=args.output_dir,
        config=config
    )
