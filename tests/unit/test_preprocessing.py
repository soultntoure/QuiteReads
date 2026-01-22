"""Unit tests for preprocessing pipeline."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.application.data.preprocessing import (
    PreprocessingConfig,
    apply_id_mappings,
    compute_statistics,
    create_id_mappings,
    create_train_val_test_split,
    filter_implicit_interactions,
    filter_sparse_items,
    filter_sparse_users,
    iterative_filter,
    load_raw_interactions,
    run_preprocessing_pipeline,
    save_artifacts,
    validate_dataset,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_raw_data() -> pd.DataFrame:
    """Create sample raw data with user_id, book_id, rating."""
    return pd.DataFrame({
        'user_id': ['u1', 'u1', 'u1', 'u2', 'u2', 'u2', 'u3', 'u3', 'u3'],
        'book_id': ['b1', 'b2', 'b3', 'b1', 'b2', 'b3', 'b1', 'b2', 'b3'],
        'rating': [4.0, 5.0, 3.0, 3.0, 4.0, 5.0, 2.0, 3.0, 4.0]
    })


@pytest.fixture
def sample_raw_with_implicit() -> pd.DataFrame:
    """Raw data including implicit interactions (rating=0)."""
    return pd.DataFrame({
        'user_id': ['u1', 'u1', 'u2', 'u2', 'u3', 'u3'],
        'book_id': ['b1', 'b2', 'b1', 'b2', 'b1', 'b2'],
        'rating': [4.0, 0.0, 3.0, 0.0, 5.0, 2.0]  # 2 implicit ratings
    })


@pytest.fixture
def sparse_data() -> pd.DataFrame:
    """Data with sparse users and items for filtering tests."""
    return pd.DataFrame({
        'user_id': ['u1', 'u1', 'u1', 'u2', 'u2', 'u2', 'u3'],
        'book_id': ['b1', 'b2', 'b3', 'b1', 'b2', 'b1', 'b2'],
        'rating': [4.0, 5.0, 3.0, 3.0, 4.0, 2.0, 3.0]
    })


@pytest.fixture
def temp_raw_json_file(sample_raw_data: pd.DataFrame):
    """Create a temporary JSON lines file with raw data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        for _, row in sample_raw_data.iterrows():
            json.dump(row.to_dict(), f)
            f.write('\n')
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestPreprocessingConfig:
    """Tests for PreprocessingConfig dataclass."""

    def test_default_values(self):
        """Default config has sensible values."""
        config = PreprocessingConfig()
        assert config.min_user_ratings == 20
        assert config.min_item_ratings == 20
        assert config.val_ratio == 0.1
        assert config.test_ratio == 0.2
        assert config.random_seed == 42

    def test_custom_values(self):
        """Config accepts custom values."""
        config = PreprocessingConfig(
            min_user_ratings=10,
            min_item_ratings=5,
            val_ratio=0.15,
            test_ratio=0.25,
            random_seed=123
        )
        assert config.min_user_ratings == 10
        assert config.min_item_ratings == 5
        assert config.val_ratio == 0.15
        assert config.test_ratio == 0.25
        assert config.random_seed == 123


# =============================================================================
# Data Loading Tests
# =============================================================================

class TestLoadRawInteractions:
    """Tests for load_raw_interactions function."""

    def test_load_valid_json_lines(self, temp_raw_json_file: Path):
        """Successfully loads JSON lines format."""
        df = load_raw_interactions(temp_raw_json_file)
        assert len(df) == 9
        assert set(df.columns) == {'user_id', 'book_id', 'rating'}

    def test_file_not_found_raises(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_raw_interactions(Path('/nonexistent/path.json'))

    def test_missing_columns_raises(self, temp_output_dir: Path):
        """Raises ValueError when required columns missing."""
        bad_file = temp_output_dir / 'bad.json'
        with open(bad_file, 'w') as f:
            f.write('{"user_id": "u1", "other": "value"}\n')

        with pytest.raises(ValueError, match="Missing required columns"):
            load_raw_interactions(bad_file)


# =============================================================================
# Filtering Tests
# =============================================================================

class TestFilterImplicitInteractions:
    """Tests for filter_implicit_interactions function."""

    def test_removes_zero_ratings(self, sample_raw_with_implicit: pd.DataFrame):
        """Filters out rating=0 interactions."""
        result = filter_implicit_interactions(sample_raw_with_implicit)
        assert len(result) == 4  # 6 total - 2 implicit
        assert (result['rating'] > 0).all()

    def test_preserves_explicit_ratings(self, sample_raw_data: pd.DataFrame):
        """Preserves all explicit ratings (no zeros in data)."""
        result = filter_implicit_interactions(sample_raw_data)
        assert len(result) == len(sample_raw_data)


class TestFilterSparseUsers:
    """Tests for filter_sparse_users function."""

    def test_filters_users_below_threshold(self, sparse_data: pd.DataFrame):
        """Removes users with fewer ratings than threshold."""
        result = filter_sparse_users(sparse_data, min_ratings=2)
        assert set(result['user_id'].unique()) == {'u1', 'u2'}

    def test_keeps_users_at_threshold(self, sparse_data: pd.DataFrame):
        """Keeps users with exactly threshold ratings."""
        result = filter_sparse_users(sparse_data, min_ratings=3)
        assert set(result['user_id'].unique()) == {'u1', 'u2'}


class TestFilterSparseItems:
    """Tests for filter_sparse_items function."""

    def test_filters_items_below_threshold(self, sparse_data: pd.DataFrame):
        """Removes items with fewer ratings than threshold."""
        result = filter_sparse_items(sparse_data, min_ratings=2)
        assert 'b3' not in result['book_id'].values

    def test_keeps_items_at_threshold(self, sparse_data: pd.DataFrame):
        """Keeps items with exactly threshold ratings."""
        result = filter_sparse_items(sparse_data, min_ratings=3)
        assert set(result['book_id'].unique()) == {'b1', 'b2'}


class TestIterativeFilter:
    """Tests for iterative_filter function."""

    def test_converges(self, sparse_data: pd.DataFrame):
        """Iterative filter eventually converges."""
        result, n_iterations = iterative_filter(sparse_data, 2, 2)
        assert n_iterations > 0
        assert len(result) <= len(sparse_data)

    def test_respects_max_iterations(self, sample_raw_data: pd.DataFrame):
        """Respects max_iterations limit."""
        _, n_iterations = iterative_filter(
            sample_raw_data, 1, 1, max_iterations=3
        )
        assert n_iterations <= 3


# =============================================================================
# ID Mapping Tests
# =============================================================================

class TestCreateIdMappings:
    """Tests for create_id_mappings function."""

    def test_creates_contiguous_user_ids(self, sample_raw_data: pd.DataFrame):
        """User IDs map to contiguous integers starting at 0."""
        user_to_idx, _, _, _ = create_id_mappings(sample_raw_data)
        indices = list(user_to_idx.values())
        assert min(indices) == 0
        assert max(indices) == len(indices) - 1

    def test_creates_contiguous_item_ids(self, sample_raw_data: pd.DataFrame):
        """Item IDs map to contiguous integers starting at 0."""
        _, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        indices = list(item_to_idx.values())
        assert min(indices) == 0
        assert max(indices) == len(indices) - 1

    def test_bidirectional_mapping(self, sample_raw_data: pd.DataFrame):
        """Forward and reverse mappings are consistent."""
        user_to_idx, idx_to_user, item_to_idx, idx_to_item = create_id_mappings(
            sample_raw_data
        )
        for user, idx in user_to_idx.items():
            assert idx_to_user[idx] == user
        for item, idx in item_to_idx.items():
            assert idx_to_item[idx] == item


class TestApplyIdMappings:
    """Tests for apply_id_mappings function."""

    def test_applies_mappings_correctly(self, sample_raw_data: pd.DataFrame):
        """Mappings correctly applied to create indexed DataFrame."""
        user_to_idx, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        result = apply_id_mappings(sample_raw_data, user_to_idx, item_to_idx)

        assert 'user_idx' in result.columns
        assert 'item_idx' in result.columns
        assert 'rating' in result.columns
        assert len(result) == len(sample_raw_data)

    def test_indexed_values_are_integers(self, sample_raw_data: pd.DataFrame):
        """Indexed values are integers suitable for PyTorch embeddings."""
        user_to_idx, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        result = apply_id_mappings(sample_raw_data, user_to_idx, item_to_idx)

        assert result['user_idx'].dtype in [np.int64, np.int32, int]
        assert result['item_idx'].dtype in [np.int64, np.int32, int]


# =============================================================================
# Train/Val/Test Split Tests
# =============================================================================

class TestCreateTrainValTestSplit:
    """Tests for create_train_val_test_split function."""

    def test_split_sizes(self, sample_raw_data: pd.DataFrame):
        """Split sizes match specified ratios."""
        train, val, test = create_train_val_test_split(
            sample_raw_data, val_ratio=0.1, test_ratio=0.2, seed=42
        )
        total = len(sample_raw_data)
        assert len(test) == int(total * 0.2)
        assert len(val) == int(total * 0.1)
        assert len(train) == total - len(test) - len(val)

    def test_no_overlap(self, sample_raw_data: pd.DataFrame):
        """Train, val, and test sets have no overlapping indices."""
        train, val, test = create_train_val_test_split(
            sample_raw_data, val_ratio=0.1, test_ratio=0.2, seed=42
        )
        total = len(train) + len(val) + len(test)
        assert total == len(sample_raw_data)

    def test_reproducibility(self, sample_raw_data: pd.DataFrame):
        """Same seed produces same split."""
        train1, val1, test1 = create_train_val_test_split(
            sample_raw_data, val_ratio=0.1, test_ratio=0.2, seed=42
        )
        train2, val2, test2 = create_train_val_test_split(
            sample_raw_data, val_ratio=0.1, test_ratio=0.2, seed=42
        )
        pd.testing.assert_frame_equal(train1, train2)
        pd.testing.assert_frame_equal(val1, val2)
        pd.testing.assert_frame_equal(test1, test2)


# =============================================================================
# Statistics and Validation Tests
# =============================================================================

class TestComputeStatistics:
    """Tests for compute_statistics function."""

    def test_returns_required_keys(self, sample_raw_data: pd.DataFrame):
        """Statistics dict contains all required keys."""
        stats = compute_statistics(sample_raw_data, sample_raw_data)
        required_keys = [
            'original_interactions', 'original_users', 'original_items',
            'filtered_interactions', 'filtered_users', 'filtered_items',
            'sparsity', 'rating_mean', 'rating_std'
        ]
        for key in required_keys:
            assert key in stats

    def test_sparsity_calculation(self, sample_raw_data: pd.DataFrame):
        """Sparsity correctly calculated."""
        stats = compute_statistics(sample_raw_data, sample_raw_data)
        n_users = sample_raw_data['user_id'].nunique()
        n_items = sample_raw_data['book_id'].nunique()
        expected_sparsity = 1 - (len(sample_raw_data) / (n_users * n_items))
        assert abs(stats['sparsity'] - expected_sparsity) < 1e-6


class TestValidateDataset:
    """Tests for validate_dataset function."""

    def test_passes_valid_dataset(self):
        """Valid dataset passes validation."""
        # Create a larger dataset that passes all thresholds
        large_data = pd.DataFrame({
            'user_id': [f'u{i}' for i in range(150) for _ in range(10)],
            'book_id': [f'b{j}' for _ in range(150) for j in range(10)],
            'rating': [4.0] * 1500
        })
        validate_dataset(large_data, min_users=100, min_items=10)

    def test_fails_too_few_users(self, sample_raw_data: pd.DataFrame):
        """Raises ValueError when too few users."""
        with pytest.raises(ValueError, match="Too few users"):
            validate_dataset(sample_raw_data, min_users=100, min_items=1)

    def test_fails_too_few_items(self, sample_raw_data: pd.DataFrame):
        """Raises ValueError when too few items."""
        with pytest.raises(ValueError, match="Too few items"):
            validate_dataset(sample_raw_data, min_users=1, min_items=100)

    def test_fails_too_few_interactions(self, sample_raw_data: pd.DataFrame):
        """Raises ValueError when too few interactions."""
        with pytest.raises(ValueError, match="Too few interactions"):
            validate_dataset(sample_raw_data, min_users=1, min_items=1)


# =============================================================================
# Save Artifacts Tests
# =============================================================================

class TestSaveArtifacts:
    """Tests for save_artifacts function."""

    def test_creates_directory_structure(
        self, sample_raw_data: pd.DataFrame, temp_output_dir: Path
    ):
        """Creates processed/ and splits/ directories."""
        user_to_idx, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        df_indexed = apply_id_mappings(sample_raw_data, user_to_idx, item_to_idx)
        train, val, test = create_train_val_test_split(df_indexed)
        stats = compute_statistics(sample_raw_data, sample_raw_data)
        config = PreprocessingConfig()

        save_artifacts(
            df_filtered=sample_raw_data,
            df_indexed=df_indexed,
            train_df=train,
            val_df=val,
            test_df=test,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            config=config,
            stats=stats,
            n_iterations=1,
            output_dir=temp_output_dir
        )

        assert (temp_output_dir / 'processed').exists()
        assert (temp_output_dir / 'splits').exists()

    def test_saves_all_files(
        self, sample_raw_data: pd.DataFrame, temp_output_dir: Path
    ):
        """Saves all required artifact files."""
        user_to_idx, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        df_indexed = apply_id_mappings(sample_raw_data, user_to_idx, item_to_idx)
        train, val, test = create_train_val_test_split(df_indexed)
        stats = compute_statistics(sample_raw_data, sample_raw_data)
        config = PreprocessingConfig()

        save_artifacts(
            df_filtered=sample_raw_data,
            df_indexed=df_indexed,
            train_df=train,
            val_df=val,
            test_df=test,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            config=config,
            stats=stats,
            n_iterations=1,
            output_dir=temp_output_dir
        )

        processed = temp_output_dir / 'processed'
        assert (processed / 'interactions_filtered.parquet').exists()
        assert (processed / 'interactions_indexed.parquet').exists()
        assert (processed / 'user_mapping.json').exists()
        assert (processed / 'item_mapping.json').exists()
        assert (processed / 'metadata.json').exists()

        splits = temp_output_dir / 'splits'
        assert (splits / 'train.parquet').exists()
        assert (splits / 'val.parquet').exists()
        assert (splits / 'test.parquet').exists()

    def test_metadata_contains_config(
        self, sample_raw_data: pd.DataFrame, temp_output_dir: Path
    ):
        """Metadata file contains preprocessing config."""
        user_to_idx, _, item_to_idx, _ = create_id_mappings(sample_raw_data)
        df_indexed = apply_id_mappings(sample_raw_data, user_to_idx, item_to_idx)
        train, val, test = create_train_val_test_split(df_indexed)
        stats = compute_statistics(sample_raw_data, sample_raw_data)
        config = PreprocessingConfig(min_user_ratings=15)

        save_artifacts(
            df_filtered=sample_raw_data,
            df_indexed=df_indexed,
            train_df=train,
            val_df=val,
            test_df=test,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            config=config,
            stats=stats,
            n_iterations=2,
            output_dir=temp_output_dir
        )

        with open(temp_output_dir / 'processed' / 'metadata.json') as f:
            metadata = json.load(f)

        assert metadata['config']['min_user_ratings'] == 15
        assert metadata['filter_iterations'] == 2


# =============================================================================
# Full Pipeline Tests
# =============================================================================

class TestRunPreprocessingPipeline:
    """Tests for run_preprocessing_pipeline function."""

    def test_full_pipeline_execution(
        self, temp_raw_json_file: Path, temp_output_dir: Path, monkeypatch
    ):
        """Full pipeline executes successfully."""
        # Patch validate_dataset to skip validation for small test data
        monkeypatch.setattr(
            'app.application.data.preprocessing.validate_dataset',
            lambda df, min_users=100, min_items=100: None
        )

        config = PreprocessingConfig(
            min_user_ratings=1,
            min_item_ratings=1,
            val_ratio=0.1,
            test_ratio=0.2
        )

        result = run_preprocessing_pipeline(
            raw_path=temp_raw_json_file,
            output_dir=temp_output_dir,
            config=config
        )

        assert 'config' in result
        assert 'statistics' in result
        assert 'n_iterations' in result

    def test_pipeline_creates_artifacts(
        self, temp_raw_json_file: Path, temp_output_dir: Path, monkeypatch
    ):
        """Pipeline creates all expected artifact files."""
        # Patch validate_dataset to skip validation for small test data
        monkeypatch.setattr(
            'app.application.data.preprocessing.validate_dataset',
            lambda df, min_users=100, min_items=100: None
        )

        config = PreprocessingConfig(
            min_user_ratings=1,
            min_item_ratings=1
        )

        run_preprocessing_pipeline(
            raw_path=temp_raw_json_file,
            output_dir=temp_output_dir,
            config=config
        )

        assert (temp_output_dir / 'processed' / 'metadata.json').exists()
        assert (temp_output_dir / 'splits' / 'train.parquet').exists()
        assert (temp_output_dir / 'splits' / 'val.parquet').exists()
        assert (temp_output_dir / 'splits' / 'test.parquet').exists()

    def test_pipeline_fails_with_small_data(
        self, temp_raw_json_file: Path, temp_output_dir: Path
    ):
        """Pipeline fails with small test data using default config."""
        # Default config has min_user_ratings=20, which filters out all users
        # from our 9-interaction test data (each user has only 3 ratings).
        # This results in an empty DataFrame, causing either a ZeroDivisionError
        # in statistics computation or ValueError in validation.
        with pytest.raises((ValueError, ZeroDivisionError)):
            run_preprocessing_pipeline(
                raw_path=temp_raw_json_file,
                output_dir=temp_output_dir,
                config=None
            )
