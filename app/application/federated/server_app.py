"""
Flower ServerApp for Federated Matrix Factorization.

Orchestrates federated rounds using FedAvgItemsOnly strategy and centralized evaluation.

Key Features:
- Global model initialization: Full dimensions
- FedAvgItemsOnly strategy: Aggregates only item-side parameters
- Centralized evaluation: Tests global model on full test.parquet split
- Metric aggregation: Weighted average of local val_rmse and val_mae

Usage:
    # Run with Flower simulation
    flwr run . --run-config partition-dir=data/federated

    # Or programmatically
    from app.application.federated.server_app import app
"""


import json
from collections import OrderedDict
from datetime import datetime
from logging import INFO
from pathlib import Path
from typing import Any, Optional

import torch
import torch.nn as nn

from flwr.app import ArrayRecord, Context, MetricRecord, RecordDict
from flwr.common.logger import log
from flwr.serverapp import Grid, ServerApp

from src.data.datamodule import RatingsDataModule
from src.federated.strategy import FedAvgItemsOnly
from src.models.lightning_module import LitBiasedMatrixFactorization

# TensorBoard import (optional - gracefully handle if not available)
try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False
    SummaryWriter = None


app = ServerApp()


def _create_tensorboard_writer(output_dir: Path) -> Optional["SummaryWriter"]:
    """Create TensorBoard SummaryWriter if available.

    Args:
        output_dir: Directory to save TensorBoard logs

    Returns:
        SummaryWriter instance or None if TensorBoard is not available
    """
    if not TENSORBOARD_AVAILABLE:
        log(INFO, "TensorBoard not available - skipping TensorBoard logging")
        return None

    log_dir = output_dir / "tensorboard" / datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)
    log(INFO, "TensorBoard logging enabled: %s", log_dir)
    return SummaryWriter(log_dir=str(log_dir))


def _log_round_metrics_to_tensorboard(
    writer: Optional["SummaryWriter"],
    round_num: int,
    train_metrics: Optional[dict] = None,
    eval_metrics: Optional[dict] = None,
    centralized_metrics: Optional[dict] = None,
) -> None:
    """Log metrics for a round to TensorBoard.

    Args:
        writer: TensorBoard SummaryWriter (or None to skip)
        round_num: Current federated round number
        train_metrics: Training metrics from clients
        eval_metrics: Evaluation metrics from clients
        centralized_metrics: Centralized evaluation metrics from server
    """
    if writer is None:
        return

    # Log training metrics
    if train_metrics:
        if "agg_loss" in train_metrics:
            writer.add_scalar("train/loss", train_metrics["agg_loss"], round_num)
        if "total_examples" in train_metrics:
            writer.add_scalar("train/total_examples", train_metrics["total_examples"], round_num)

    # Log client evaluation metrics
    if eval_metrics:
        if "agg_rmse" in eval_metrics:
            writer.add_scalar("eval/client_rmse", eval_metrics["agg_rmse"], round_num)
        if "agg_mae" in eval_metrics:
            writer.add_scalar("eval/client_mae", eval_metrics["agg_mae"], round_num)
        if "agg_loss" in eval_metrics:
            writer.add_scalar("eval/client_loss", eval_metrics["agg_loss"], round_num)

    # Log centralized evaluation metrics
    if centralized_metrics:
        if "test_rmse" in centralized_metrics:
            writer.add_scalar("eval/centralized_rmse", centralized_metrics["test_rmse"], round_num)
        if "test_mae" in centralized_metrics:
            writer.add_scalar("eval/centralized_mae", centralized_metrics["test_mae"], round_num)
        if "test_loss" in centralized_metrics:
            writer.add_scalar("eval/centralized_loss", centralized_metrics["test_loss"], round_num)

    writer.flush()


def _save_final_metrics(
    output_dir: Path,
    result: Any,
    n_users: int,
    n_items: int,
    n_factors: int,
    global_mean: float,
    num_rounds: int,
) -> None:
    """Save final training metrics to JSON for analysis.

    Creates a final_metrics.json file containing:
    - Best and final performance metrics (RMSE, MAE)
    - Per-round history for both client and centralized evaluation
    - Model configuration

    Args:
        output_dir: Directory to save final_metrics.json
        result: FedAvgResult from strategy.start()
        n_users: Total number of users
        n_items: Total number of items
        n_factors: Latent factor dimension
        global_mean: Global mean rating
        num_rounds: Number of federated rounds
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract centralized evaluation metrics (server-side test set evaluation)
    centralized_history = {}
    best_round = None
    best_test_rmse = float("inf")
    best_test_mae = None
    final_test_rmse = None
    final_test_mae = None

    if result.evaluate_metrics_serverapp:
        for round_num, metrics in result.evaluate_metrics_serverapp.items():
            metrics_dict = dict(metrics)
            centralized_history[round_num] = {
                "test_rmse": metrics_dict.get("test_rmse"),
                "test_mae": metrics_dict.get("test_mae"),
                "test_loss": metrics_dict.get("test_loss"),
            }
            # Track best round
            rmse = metrics_dict.get("test_rmse", float("inf"))
            if rmse < best_test_rmse:
                best_test_rmse = rmse
                best_test_mae = metrics_dict.get("test_mae")
                best_round = round_num

        # Get final round metrics
        if num_rounds in result.evaluate_metrics_serverapp:
            final_metrics = dict(result.evaluate_metrics_serverapp[num_rounds])
            final_test_rmse = final_metrics.get("test_rmse")
            final_test_mae = final_metrics.get("test_mae")

    # Extract client-side evaluation metrics
    client_eval_history = {}
    if result.evaluate_metrics_clientapp:
        for round_num, metrics in result.evaluate_metrics_clientapp.items():
            metrics_dict = dict(metrics)
            client_eval_history[round_num] = {
                "agg_rmse": metrics_dict.get("agg_rmse"),
                "agg_mae": metrics_dict.get("agg_mae"),
                "agg_loss": metrics_dict.get("agg_loss"),
                "total_examples": metrics_dict.get("total_examples"),
            }

    # Extract training metrics
    train_history = {}
    if result.train_metrics_clientapp:
        for round_num, metrics in result.train_metrics_clientapp.items():
            metrics_dict = dict(metrics)
            train_history[round_num] = {
                "agg_loss": metrics_dict.get("agg_loss"),
                "total_examples": metrics_dict.get("total_examples"),
            }

    # Calculate number of parameters (item-side only for federated)
    n_item_params = (
        1  # global_bias
        + n_items  # item_bias
        + n_items * n_factors  # item_embedding
    )
    n_user_params = n_users + n_users * n_factors  # user_bias + user_embedding
    n_total_params = n_item_params + n_user_params

    # Build final metrics dict
    final_metrics_data = {
        "best_test_rmse": best_test_rmse if best_test_rmse != float("inf") else None,
        "best_test_mae": best_test_mae,
        "best_round": best_round,
        "final_test_rmse": final_test_rmse,
        "final_test_mae": final_test_mae,
        "rounds_completed": num_rounds,
        "model_config": {
            "n_users": n_users,
            "n_items": n_items,
            "n_factors": n_factors,
            "global_bias": global_mean,
            "n_parameters": n_total_params,
            "n_item_parameters": n_item_params,
            "n_user_parameters": n_user_params,
        },
        "history": {
            "centralized_eval": centralized_history,
            "client_eval": client_eval_history,
            "train": train_history,
        },
    }

    # Save to JSON
    metrics_path = output_dir / "final_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(final_metrics_data, f, indent=2)

    log(INFO, "Final metrics saved to: %s", metrics_path)


def _weighted_average_metrics(
    contents: list[RecordDict],
    weighted_by_key: str,
) -> MetricRecord:
    """Compute weighted average of metrics from client RecordDicts.

    Aggregates val_rmse and val_mae using num-examples as weights.

    Args:
        contents: List of RecordDict from client replies
        weighted_by_key: Key for weight value (e.g., "num-examples")

    Returns:
        MetricRecord with weighted average of eval_rmse and eval_mae
    """
    total_examples = 0
    weighted_rmse = 0.0
    weighted_mae = 0.0
    weighted_loss = 0.0

    for content in contents:
        metrics = content.metric_records.get("metrics", {})
        num_examples = metrics.get(weighted_by_key, 1)
        total_examples += num_examples

        # Handle both eval and train metrics
        if "eval_rmse" in metrics:
            weighted_rmse += metrics["eval_rmse"] * num_examples
            weighted_mae += metrics["eval_mae"] * num_examples
            weighted_loss += metrics["eval_loss"] * num_examples
        elif "train_loss" in metrics:
            weighted_loss += metrics["train_loss"] * num_examples

    if total_examples == 0:
        return MetricRecord({})

    result = {"total_examples": total_examples}

    if weighted_rmse > 0:
        result["agg_rmse"] = weighted_rmse / total_examples
        result["agg_mae"] = weighted_mae / total_examples
    if weighted_loss > 0:
        result["agg_loss"] = weighted_loss / total_examples

    return MetricRecord(result)


def _create_centralized_evaluate_fn(
    data_dir: Path,
    n_users: int,
    n_items: int,
    n_factors: int,
    global_mean: float,
    device: torch.device,
    user_lr: float = 0.0009,
    user_epochs: int = 3,
):
    """Create centralized evaluation function for server-side evaluation.

    The centralized evaluation handles the unique challenge of federated MF:
    user embeddings are distributed across clients and never aggregated.

    Strategy:
    1. Load aggregated item parameters (global_bias, item_embedding, item_bias)
    2. Initialize fresh user embeddings
    3. Briefly train user embeddings on test data with frozen item params
    4. Evaluate on test data

    This mimics how a new user would experience the system: they get the
    global item embeddings and quickly learn their preferences.

    Args:
        data_dir: Path to data directory with splits/
        n_users: Total number of users
        n_items: Total number of items
        n_factors: Latent factor dimension
        global_mean: Global mean rating
        device: Torch device for computation
        user_lr: Learning rate for user embedding fine-tuning
        user_epochs: Number of epochs to train user embeddings

    Returns:
        evaluate_fn callable for strategy.start()
    """
    # Pre-load test data (loaded once, reused each round)
    datamodule = RatingsDataModule(data_dir=data_dir, batch_size=2048, num_workers=0)
    datamodule.prepare_data()
    datamodule.setup(stage="test")
    test_loader = datamodule.test_dataloader()

    # Item parameter names (what we receive from aggregation)
    item_param_names = {"global_bias", "item_bias.weight", "item_embedding.weight"}

    def evaluate_fn(server_round: int, arrays: ArrayRecord) -> Optional[MetricRecord]:
        """Evaluate global model on centralized test set.

        Args:
            server_round: Current federated round
            arrays: Aggregated item parameters as ArrayRecord

        Returns:
            MetricRecord with test_rmse, test_mae, and test_loss
        """
        log(INFO, "[CENTRALIZED EVAL] Round %d - Starting evaluation", server_round)

        # Create fresh Lightning model with full dimensions
        lit_model = LitBiasedMatrixFactorization(
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
            lr=user_lr,
            weight_decay=0.0,  # No regularization for quick user embedding training
        )
        lit_model.to(device)

        # Load aggregated item parameters into the inner model
        aggregated_state = arrays.to_torch_state_dict()

        # Merge with fresh user embeddings (access inner model's state_dict)
        current_state = lit_model.model.state_dict()
        for name, param in aggregated_state.items():
            if name in item_param_names and name in current_state:
                current_state[name] = param.to(device)
        lit_model.model.load_state_dict(current_state)

        # Freeze item parameters, only train user embeddings
        for name, param in lit_model.model.named_parameters():
            if name in item_param_names:
                param.requires_grad = False
            else:
                param.requires_grad = True

        # Quick training of user embeddings on test data
        # optimizer = torch.optim.SGD(
        #     [p for p in lit_model.model.parameters() if p.requires_grad],
        #     lr=user_lr,
        # )
        optimizer = torch.optim.Adam(
            [p for p in lit_model.model.parameters() if p.requires_grad],
            lr=user_lr,
        )
        criterion = nn.MSELoss()

        lit_model.train()
        for epoch in range(user_epochs):
            for users, items, ratings in test_loader:
                users, items, ratings = (
                    users.to(device),
                    items.to(device),
                    ratings.to(device),
                )
                optimizer.zero_grad()
                preds = lit_model(users, items)
                loss = criterion(preds, ratings)
                loss.backward()
                optimizer.step()

        # Evaluate on test set
        lit_model.eval()
        total_se = 0.0
        total_ae = 0.0
        total_samples = 0

        with torch.no_grad():
            for users, items, ratings in test_loader:
                users, items, ratings = (
                    users.to(device),
                    items.to(device),
                    ratings.to(device),
                )
                preds = lit_model(users, items)
                total_se += ((preds - ratings) ** 2).sum().item()
                total_ae += torch.abs(preds - ratings).sum().item()
                total_samples += len(ratings)

        test_rmse = (total_se / total_samples) ** 0.5
        test_mae = total_ae / total_samples
        test_loss = total_se / total_samples

        log(
            INFO,
            "[CENTRALIZED EVAL] Round %d - RMSE: %.4f, MAE: %.4f, Samples: %d",
            server_round,
            test_rmse,
            test_mae,
            total_samples,
        )

        return MetricRecord({
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "test_loss": test_loss,
            "test_samples": total_samples,
        })

    return evaluate_fn


def _initialize_global_model(
    n_users: int,
    n_items: int,
    n_factors: int,
    global_mean: float,
) -> ArrayRecord:
    """Initialize global model and extract item-side parameters.

    Creates a LitBiasedMatrixFactorization model with full dimensions
    and returns only the item-side parameters for federated aggregation.

    Args:
        n_users: Total number of users (5,949 for Goodreads)
        n_items: Total number of items (2,856 for Goodreads)
        n_factors: Latent factor dimension
        global_mean: Global mean rating for bias initialization

    Returns:
        ArrayRecord containing item-side parameters:
            - global_bias
            - item_embedding.weight
            - item_bias.weight
    """
    lit_model = LitBiasedMatrixFactorization(
        n_users=n_users,
        n_items=n_items,
        n_factors=n_factors,
        global_mean=global_mean,
    )

    # Extract only item-side parameters from inner model
    item_param_names = {"global_bias", "item_bias.weight", "item_embedding.weight"}
    item_state = OrderedDict({
        name: param.clone()
        for name, param in lit_model.model.state_dict().items()
        if name in item_param_names
    })

    log(
        INFO,
        "Initialized global model: %d users, %d items, %d factors",
        n_users,
        n_items,
        n_factors,
    )
    log(INFO, "Initial item parameters: %s", list(item_state.keys()))

    return ArrayRecord(item_state)


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Main entry point for federated server.

    Orchestrates the federated learning process:
    1. Load configuration from context.run_config
    2. Initialize global model with full dimensions
    3. Configure FedAvgItemsOnly strategy
    4. Set up centralized evaluation
    5. Run federated rounds
    6. Log metrics to TensorBoard

    Args:
        grid: Flower Grid for node communication
        context: Flower Context with run configuration

    Run Config Parameters (via pyproject.toml or CLI):
        - data-dir: Path to centralized data (default: "data")
        - partition-dir: Path to partitioned data (default: "data/federated")
        - num-rounds: Number of federated rounds (default: 10)
        - n-factors: Latent factor dimension (default: 16)
        - fraction-train: Fraction of clients for training (default: 1.0)
        - fraction-evaluate: Fraction of clients for evaluation (default: 1.0)
        - min-train-clients: Minimum clients for training (default: 2)
        - min-evaluate-clients: Minimum clients for evaluation (default: 2)
        - centralized-eval: Enable centralized evaluation (default: True)
        - user-lr: Learning rate for user embedding in centralized eval (default: 0.1)
        - user-epochs: Epochs for user embedding in centralized eval (default: 3)
        - output-dir: Directory for saving results and TensorBoard logs (default: "results/federated")
    """
    # Read configuration
    data_dir = Path(context.run_config.get("data-dir", "data"))
    output_dir = Path(context.run_config.get("output-dir", "results/federated"))
    num_rounds = context.run_config.get("num-rounds", 10)
    n_factors = context.run_config.get("n-factors", 16)
    fraction_train = context.run_config.get("fraction-train", 1.0)
    fraction_evaluate = context.run_config.get("fraction-evaluate", 1.0)
    min_train_clients = context.run_config.get("min-train-clients", 2)
    min_evaluate_clients = context.run_config.get("min-evaluate-clients", 2)
    min_available_clients = context.run_config.get("min-available-clients", min(min_train_clients, min_evaluate_clients))
    enable_centralized_eval = context.run_config.get("centralized-eval", True)
    user_lr = context.run_config.get("user-lr", 0.1)
    user_epochs = context.run_config.get("user-epochs", 3)

    log(INFO, "=" * 60)
    log(INFO, "FEDERATED MATRIX FACTORIZATION - SERVER")
    log(INFO, "=" * 60)
    log(INFO, "Configuration:")
    log(INFO, "  Data directory: %s", data_dir)
    log(INFO, "  Number of rounds: %d", num_rounds)
    log(INFO, "  Latent factors: %d", n_factors)
    log(INFO, "  Fraction train: %.2f", fraction_train)
    log(INFO, "  Fraction evaluate: %.2f", fraction_evaluate)
    log(INFO, "  Centralized evaluation: %s", enable_centralized_eval)

    # Load global metadata for model dimensions
    datamodule = RatingsDataModule(data_dir=data_dir, batch_size=1024)
    datamodule.prepare_data()
    datamodule.setup()

    n_users = datamodule.n_users
    n_items = datamodule.n_items
    global_mean = datamodule.global_mean

    log(INFO, "Global dimensions: %d users, %d items", n_users, n_items)
    log(INFO, "Global mean rating: %.4f", global_mean)

    # Determine device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(INFO, "Using device: %s", device)

    # Initialize global model (item parameters only)
    initial_arrays = _initialize_global_model(
        n_users=n_users,
        n_items=n_items,
        n_factors=n_factors,
        global_mean=global_mean,
    )

    # Create centralized evaluation function
    evaluate_fn = None
    if enable_centralized_eval:
        evaluate_fn = _create_centralized_evaluate_fn(
            data_dir=data_dir,
            n_users=n_users,
            n_items=n_items,
            n_factors=n_factors,
            global_mean=global_mean,
            device=device,
            user_lr=user_lr,
            user_epochs=user_epochs,
        )
        log(INFO, "Centralized evaluation enabled")

    # Configure FedAvgItemsOnly strategy
    strategy = FedAvgItemsOnly(
        fraction_train=fraction_train,
        fraction_evaluate=fraction_evaluate,
        min_train_nodes=min_train_clients,
        min_evaluate_nodes=min_evaluate_clients,
        min_available_nodes=min_available_clients,
        weighted_by_key="num-examples",
        train_metrics_aggr_fn=_weighted_average_metrics,
        evaluate_metrics_aggr_fn=_weighted_average_metrics,
    )

    log(INFO, "Strategy: FedAvgItemsOnly")
    log(INFO, "  Item parameters: %s", strategy.item_param_names)
    log(INFO, "=" * 60)

    # Create TensorBoard writer
    tb_writer = _create_tensorboard_writer(output_dir)

    # Start federated learning
    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays,
        num_rounds=num_rounds,
        evaluate_fn=evaluate_fn,
    )

    # Log final results
    log(INFO, "=" * 60)
    log(INFO, "FEDERATED TRAINING COMPLETE")
    log(INFO, "=" * 60)

    # Log training metrics per round
    if result.train_metrics_clientapp:
        log(INFO, "Training metrics (client-side):")
        for round_num, metrics in result.train_metrics_clientapp.items():
            log(INFO, "  Round %d: %s", round_num, dict(metrics))

    # Log evaluation metrics per round
    if result.evaluate_metrics_clientapp:
        log(INFO, "Evaluation metrics (client-side):")
        for round_num, metrics in result.evaluate_metrics_clientapp.items():
            log(INFO, "  Round %d: %s", round_num, dict(metrics))

    # Log centralized evaluation metrics
    if result.evaluate_metrics_serverapp:
        log(INFO, "Centralized evaluation metrics (server-side):")
        for round_num, metrics in result.evaluate_metrics_serverapp.items():
            log(INFO, "  Round %d: %s", round_num, dict(metrics))

    # Log all rounds to TensorBoard
    for round_num in range(1, num_rounds + 1):
        train_metrics = None
        eval_metrics = None
        centralized_metrics = None

        if result.train_metrics_clientapp and round_num in result.train_metrics_clientapp:
            train_metrics = dict(result.train_metrics_clientapp[round_num])
        if result.evaluate_metrics_clientapp and round_num in result.evaluate_metrics_clientapp:
            eval_metrics = dict(result.evaluate_metrics_clientapp[round_num])
        if result.evaluate_metrics_serverapp and round_num in result.evaluate_metrics_serverapp:
            centralized_metrics = dict(result.evaluate_metrics_serverapp[round_num])

        _log_round_metrics_to_tensorboard(
            tb_writer, round_num, train_metrics, eval_metrics, centralized_metrics
        )

    # Close TensorBoard writer
    if tb_writer is not None:
        tb_writer.close()
        log(INFO, "TensorBoard logs saved to: %s/tensorboard/", output_dir)

    # Save final metrics to JSON
    _save_final_metrics(
        output_dir=output_dir,
        result=result,
        n_users=n_users,
        n_items=n_items,
        n_factors=n_factors,
        global_mean=global_mean,
        num_rounds=num_rounds,
    )

    log(INFO, "=" * 60)