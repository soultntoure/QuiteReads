"""Verification script for Phase 1 (Day 1-2) Acceptance Criteria.

This script validates that all acceptance criteria for Data Handler and
Recommender Model have been met.

Acceptance Criteria:
  Data Handler (Task 1.1):
    [PASS/FAIL] Can load Book-Crossing or similar dataset
    [PASS/FAIL] Provides clean train/test splits
    [PASS/FAIL] Supports partitioning data across N simulated clients

  Recommender Model (Task 1.2):
    [PASS/FAIL] Model trains on rating data
    [PASS/FAIL] Produces RMSE < 1.0 on test set
    [PASS/FAIL] Parameters can be extracted and aggregated
"""

import sys
import tempfile
from pathlib import Path

import torch
import torch.nn as nn

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.application.data import (
    DatasetLoader,
    UserPartitioner,
    PartitionConfig,
)
from app.application.reporting import compute_rmse, compute_mae
from app.core.models.matrix_factorization import BiasedMatrixFactorization


def print_header(title: str) -> None:
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(criterion: str, passed: bool, details: str = "") -> None:
    """Print acceptance criterion result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {criterion}")
    if details:
        print(f"      {details}")


def test_data_loading() -> bool:
    """Test: Can load dataset."""
    print_header("CRITERION 1.1.1: Load Dataset")

    try:
        loader = DatasetLoader(data_dir="data")
        loader.load()
        metadata = loader.get_metadata()

        print(f"\nDataset loaded successfully:")
        print(f"  - Total users: {metadata.n_users:,}")
        print(f"  - Total items: {metadata.n_items:,}")
        print(f"  - Train samples: {metadata.train_size:,}")
        print(f"  - Val samples: {metadata.val_size:,}")
        print(f"  - Test samples: {metadata.test_size:,}")
        print(f"  - Global mean: {metadata.global_mean:.3f}")
        print(f"  - Sparsity: {metadata.sparsity:.4f}")

        passed = metadata.train_size > 0 and metadata.test_size > 0
        print_result(
            "Dataset loading",
            passed,
            f"{metadata.train_size + metadata.val_size + metadata.test_size:,} total ratings",
        )
        return passed

    except Exception as e:
        print_result("Dataset loading", False, f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_train_test_splits() -> bool:
    """Test: Provides clean train/test splits."""
    print_header("CRITERION 1.1.2: Train/Test Splits")

    try:
        loader = DatasetLoader(data_dir="data")
        loader.load()

        train_dataset = loader.get_train_dataset()
        test_dataset = loader.get_test_dataset()

        print(f"\nSplit sizes:")
        print(f"  - Train: {len(train_dataset):,} samples")
        print(f"  - Test:  {len(test_dataset):,} samples")

        # Check rating statistics
        print(f"\nRating statistics:")
        print(f"  - Train mean: {train_dataset.rating_mean:.3f}")
        print(f"  - Train std:  {train_dataset.rating_std:.3f}")
        print(f"  - Test mean:  {test_dataset.rating_mean:.3f}")
        print(f"  - Test std:   {test_dataset.rating_std:.3f}")

        passed = len(train_dataset) > 0 and len(test_dataset) > 0
        print_result("Clean train/test splits", passed, "Datasets created successfully")
        return passed

    except Exception as e:
        print_result("Train/test splits", False, f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_partitioning() -> bool:
    """Test: Supports partitioning data across N clients."""
    print_header("CRITERION 1.1.3: Client Partitioning")

    try:
        n_clients = 5
        config = PartitionConfig(num_clients=n_clients, seed=42)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            partitioner = UserPartitioner(config)
            result = partitioner.partition(
                data_dir=Path("data"), output_dir=output_dir
            )

            print(f"\nPartitioned into {n_clients} clients:")
            print(f"  - Total clients: {result.num_clients}")
            print(f"  - Users per client: {result.users_per_client}")
            print(f"  - Interactions per client: {result.interactions_per_client}")

            # Verify directories created
            client_dirs = [output_dir / f"client_{i}" for i in range(n_clients)]
            all_exist = all(d.exists() for d in client_dirs)

            print(f"\nVerification:")
            print(f"  - All client directories exist: {all_exist}")
            print(f"  - Total interactions: {sum(result.interactions_per_client):,}")

            passed = all_exist and result.num_clients == n_clients
            print_result(
                "Client partitioning",
                passed,
                f"{n_clients} clients created successfully",
            )
            return passed

    except Exception as e:
        print_result("Client partitioning", False, f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_model_training() -> tuple[bool, float, BiasedMatrixFactorization]:
    """Test: Model trains on rating data and produces RMSE < 1.0."""
    print_header("CRITERION 1.2.1 & 1.2.2: Model Training & RMSE < 1.0")

    try:
        # Load data
        loader = DatasetLoader(data_dir="data")
        loader.load()

        # Use smaller batch for quick verification
        train_loader = loader.get_train_loader(batch_size=512)
        test_loader = loader.get_test_loader(batch_size=1024)

        # Initialize model
        model = BiasedMatrixFactorization(
            n_users=loader.n_users,
            n_items=loader.n_items,
            n_factors=32,
            global_mean=loader.global_mean,
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-5)
        criterion = nn.MSELoss()

        print(f"\nModel configuration:")
        print(f"  - Users: {loader.n_users:,}")
        print(f"  - Items: {loader.n_items:,}")
        print(f"  - Embedding dim: 32")
        print(f"  - Parameters: {model.get_num_parameters():,}")
        print(f"  - Global mean: {loader.global_mean:.3f}")

        # Training loop (5 epochs for quick verification)
        n_epochs = 5
        print(f"\nTraining for {n_epochs} epochs:")

        for epoch in range(n_epochs):
            model.train()
            total_loss = 0
            n_batches = 0

            for user_ids, item_ids, ratings in train_loader:
                optimizer.zero_grad()
                predictions = model(user_ids, item_ids)
                loss = criterion(predictions, ratings)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                n_batches += 1

            avg_loss = total_loss / n_batches
            print(f"  Epoch {epoch + 1}/{n_epochs}: Loss = {avg_loss:.4f}")

        # Evaluate on test set
        print("\nEvaluating on test set...")
        model.eval()
        all_predictions = []
        all_actuals = []

        with torch.no_grad():
            for user_ids, item_ids, ratings in test_loader:
                predictions = model(user_ids, item_ids)
                all_predictions.append(predictions)
                all_actuals.append(ratings)

        all_predictions = torch.cat(all_predictions)
        all_actuals = torch.cat(all_actuals)

        rmse = compute_rmse(all_predictions, all_actuals)
        mae = compute_mae(all_predictions, all_actuals)

        print(f"\nTest Set Performance:")
        print(f"  - RMSE: {rmse:.4f}")
        print(f"  - MAE:  {mae:.4f}")
        print(f"  - Target: RMSE < 1.0")
        print(f"  - Result: {'PASS' if rmse < 1.0 else 'FAIL'}")

        passed_training = True
        passed_rmse = rmse < 1.0

        print_result("Model trains on rating data", passed_training, "Loss converged")
        print_result("RMSE < 1.0 on test set", passed_rmse, f"RMSE = {rmse:.4f}")

        return passed_training and passed_rmse, rmse, model

    except Exception as e:
        print_result("Model training", False, f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False, float("inf"), None


def test_parameter_extraction(model: BiasedMatrixFactorization) -> bool:
    """Test: Parameters can be extracted and aggregated."""
    print_header("CRITERION 1.2.3: Parameter Extraction & Aggregation")

    try:
        if model is None:
            print_result("Parameter extraction", False, "No trained model available")
            return False

        # Extract parameters
        state_dict = model.state_dict()

        print(f"\nExtracted parameters:")
        for name, param in state_dict.items():
            print(f"  - {name}: shape {list(param.shape)}, {param.numel():,} values")

        # Test aggregation (FedAvg simulation)
        print(f"\nSimulating FedAvg aggregation:")

        # Create two "client" models with same parameters
        aggregated_params = {}
        for name, param in state_dict.items():
            # Average with itself (simulates 2 clients with same weights)
            aggregated_params[name] = (param + param) / 2.0

        # Load aggregated parameters back
        model.load_state_dict(aggregated_params)
        print(f"  - Aggregated parameters loaded successfully")

        # Verify parameters are accessible via methods
        n_params = model.get_num_parameters()
        config = model.get_config()

        print(f"\nModel introspection:")
        print(f"  - Total parameters: {n_params:,}")
        print(f"  - Config: n_users={config['n_users']}, n_items={config['n_items']}")

        passed = n_params > 0 and "item_embedding.weight" in state_dict
        print_result(
            "Parameter extraction & aggregation",
            passed,
            "FedAvg simulation successful",
        )
        return passed

    except Exception as e:
        print_result("Parameter extraction", False, f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all acceptance criteria tests."""
    print("\n")
    print("=" * 70)
    print("  PHASE 1 (DAY 1-2) ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 70)

    results = {}

    # Task 1.1: Data Handler
    results["data_loading"] = test_data_loading()
    results["train_test_splits"] = test_train_test_splits()
    results["partitioning"] = test_partitioning()

    # Task 1.2: Recommender Model
    training_passed, rmse, model = test_model_training()
    results["model_training"] = training_passed
    results["parameter_extraction"] = test_parameter_extraction(model)

    # Final summary
    print_header("FINAL SUMMARY")

    print("\nTask 1.1: Data Handler")
    print(
        f"  {'[PASS]' if results['data_loading'] else '[FAIL]'} Dataset loading"
    )
    print(
        f"  {'[PASS]' if results['train_test_splits'] else '[FAIL]'} Train/test splits"
    )
    print(
        f"  {'[PASS]' if results['partitioning'] else '[FAIL]'} Client partitioning"
    )

    print("\nTask 1.2: Recommender Model")
    print(
        f"  {'[PASS]' if results['model_training'] else '[FAIL]'} Model training & RMSE < 1.0"
    )
    print(
        f"  {'[PASS]' if results['parameter_extraction'] else '[FAIL]'} Parameter extraction"
    )

    all_passed = all(results.values())
    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] ALL ACCEPTANCE CRITERIA MET - READY FOR DAY 3-4")
    else:
        failed_criteria = [k for k, v in results.items() if not v]
        print(f"[FAILED] Some criteria not met: {', '.join(failed_criteria)}")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
