# Data Management Module

## 1. Overview
The `data` directory serves as the central storage hub for all datasets used in the federated recommendation experiments. It follows a structured lifecycle: from raw data ingestion to cleaned/filtered parquet files, and finally to experimental train/val/test splits.

## 2. Purpose
This module isolates data storage from the source code, ensuring that the preprocessing pipeline is reproducible and that large datasets do not bloat the primary repository. It provides a standardized interface for the models to consume data, abstracting away the complexities of original ID mappings and sparsity filtering.

## 3. Components Breakdown

### `raw/`
*   **Responsibility**: Stores original, immutable datasets.
*   **Key Files**: `goodreads_interactions_poetry.json` (JSON Lines format).
*   **Constraints**: Read-only; should never be modified by any script.

### `processed/`
*   **Responsibility**: Stores the results of initial cleaning and sparsity filtering.
*   **Key Files**:
    *   `interactions_filtered.parquet`: The "Core" dataset after k-core filtering.
    *   `user_mapping.json` & `item_mapping.json`: Bijective mappings between original IDs and integer indices.
    *   `metadata.json`: Summary statistics used for model initialization (e.g., `n_users`, `n_items`).
*   **Logic**: Uses k-core filtering (typically k=20) to ensure every user and item has sufficient interactions for meaningful learning.

### `splits/`
*   **Responsibility**: Stores the final partitions for model training and evaluation.
*   **Key Files**: `train.parquet`, `val.parquet`, `test.parquet`.
*   **Ratio**: Typically an 80/10/10 temporal or random split.

## 4. Execution / How to Run
The data lifecycle is managed via the preprocessing script. To (re)generate the processed data and splits, run:

```powershell
python src/data/preprocessing.py
```

*Note: Ensure the raw dataset is present in `data/raw/` before execution.*

## 5. Defaults & Configuration
*   **File Format**: Parquet is used for processed data to maximize I/O performance.
*   **Filtering**: Default k-core is set to 20 for both users and books.
*   **ID Mapping**: All IDs are zero-indexed integers to facilitate embedding lookups in PyTorch.

## 6. Significance
The data used here is derived from the **Goodreads Poetry** dataset. Insights from exploratory analysis (`notebooks/poetry.ipynb`) highlight the following:

*   **Dataset Scale**: The raw dataset contains ~2.73M interactions across 377k users and 36k books.
*   **Filtering Impact**: Post-20-core filtering, the dataset converges to ~229k interactions with 5,949 users and 2,856 books, significantly reducing sparsity from 99.98% to ~98.65%.
*   **Domain Specificity**: Because the dataset is restricted to a single genre (Poetry), the latent space is expected to be more "dense" or focused.
*   **Architectural Insight**: Since users are interacting within a subset of the same genre, a **lower number of latent features** might suffice to capture user preferences effectively, compared to more diverse, multi-genre datasets.
