"""
Flower ClientApp for Federated Matrix Factorization.

Implements @app.train() and @app.evaluate() using Flower's Message API (1.25+).

Key Features:
- User embedding persistence: Stores user_embedding and user_bias in context.state
  between rounds so each client maintains its own user preferences.
- Item-only communication: Only item-side parameters are sent back to server.
- Lightning-based training: Uses LitBiasedMatrixFactorization for local training.

State Management:
    context.state["user_params"] = ArrayRecord with user_embedding.weight, user_bias.weight
    These are restored each round and never sent to the server.

Usage:
    # Run with Flower simulation or deployment
"""

from collections import OrderedDict
from pathlib import Path

import lightning as L
import torch

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from app.application.data import ClientDataModule, load_partition_config
from app.application.training.centralized_trainer import LitBiasedMatrixFactorization



# Parameter names for filtering (matches strategy.py expectations)
# We access lit_model.model.state_dict() to get these names without "model." prefix
ITEM_PARAM_NAMES = frozenset({
    "global_bias",
    "item_bias.weight",
    "item_embedding.weight",
})  # Sent to server for aggregation

USER_PARAM_NAMES = frozenset({
    "user_bias.weight",
    "user_embedding.weight",
})  # Kept local in context.state


app = ClientApp()


def _get_client_datamodule(context: Context) -> ClientDataModule:
    """Create and setup ClientDataModule from context configuration.

    Args:
        context: Flower context with node_config and run_config

    Returns:
        Configured and setup ClientDataModule
    """
    partition_id = int(context.node_config["partition-id"])
    partition_dir = Path(context.run_config.get("partition-dir", "data/federated"))

    # Load partition config for global dimensions
    config = load_partition_config(partition_dir)

    # Get global dimensions
    global_n_users = config["total_users"]
    global_n_items = config["total_items"]

    # Check for global_mean in config, otherwise will compute from local data
    global_mean = config.get("global_mean", None)

    datamodule = ClientDataModule(
        client_id=partition_id,
        partition_dir=partition_dir,
        global_n_users=global_n_users,
        global_n_items=global_n_items,
        global_mean=global_mean,
        batch_size=context.run_config.get("batch-size", 1024),
        num_workers=0,
    )
    datamodule.prepare_data()
    datamodule.setup()

    return datamodule


def _create_lit_model(
    datamodule: ClientDataModule,
    n_factors: int = 16,
    lr: float = 0.02,
    weight_decay: float = 0.005,
) -> LitBiasedMatrixFactorization:
    """Create a new LitBiasedMatrixFactorization model.

    Args:
        datamodule: ClientDataModule with global dimensions
        n_factors: Latent factor dimension
        lr: Learning rate for optimizer
        weight_decay: L2 regularization strength

    Returns:
        Initialized LitBiasedMatrixFactorization model
    """
    return LitBiasedMatrixFactorization(
        n_users=datamodule.global_n_users,
        n_items=datamodule.global_n_items,
        n_factors=n_factors,
        global_mean=datamodule.global_mean or 0.0,
        lr=lr,
        weight_decay=weight_decay,
    )


def _get_inner_state_dict(lit_model: LitBiasedMatrixFactorization) -> OrderedDict:
    """Get state_dict from the underlying BiasedMatrixFactorization model.

    This returns parameter names without 'model.' prefix, matching strategy.py.

    Args:
        lit_model: LitBiasedMatrixFactorization wrapper

    Returns:
        state_dict with keys like 'global_bias', 'item_embedding.weight', etc.
    """
    return lit_model.model.state_dict()


def _set_inner_state_dict(
    lit_model: LitBiasedMatrixFactorization,
    state_dict: OrderedDict,
) -> None:
    """Set state_dict on the underlying BiasedMatrixFactorization model.

    Args:
        lit_model: LitBiasedMatrixFactorization wrapper
        state_dict: Parameters with keys like 'global_bias', etc.
    """
    lit_model.model.load_state_dict(state_dict)


def _merge_parameters(
    server_params: dict,
    local_user_params: dict | None,
    lit_model: LitBiasedMatrixFactorization,
) -> OrderedDict:
    """Merge server (item) params with local (user) params.

    Priority:
    1. Server params for item-side (global_bias, item_embedding, item_bias)
    2. Local user params from context.state (user_embedding, user_bias)
    3. Model's initialized params as fallback

    Args:
        server_params: Parameters received from server (item-side only)
        local_user_params: User params from context.state (may be None on first round)
        lit_model: LitBiasedMatrixFactorization with initialized parameters (fallback)

    Returns:
        Complete state_dict with merged parameters
    """
    merged = OrderedDict()

    # Start with model's current state as base (from inner model)
    for name, param in _get_inner_state_dict(lit_model).items():
        merged[name] = param.clone()

    # Override with server params (item-side)
    for name, param in server_params.items():
        if name in merged:
            merged[name] = param

    # Override with local user params if available
    if local_user_params:
        for name, param in local_user_params.items():
            if name in USER_PARAM_NAMES and name in merged:
                merged[name] = param

    return merged


def _extract_item_params(state_dict: dict) -> OrderedDict:
    """Extract only item-side parameters for sending to server.

    Args:
        state_dict: Full model state_dict

    Returns:
        OrderedDict with only item-side parameters
    """
    return OrderedDict({
        name: param for name, param in state_dict.items()
        if name in ITEM_PARAM_NAMES
    })


def _extract_user_params(state_dict: dict) -> OrderedDict:
    """Extract only user-side parameters for local storage.

    Args:
        state_dict: Full model state_dict

    Returns:
        OrderedDict with only user-side parameters
    """
    return OrderedDict({
        name: param for name, param in state_dict.items()
        if name in USER_PARAM_NAMES
    })


@app.train()
def train(msg: Message, context: Context) -> Message:
    """Train the model on local client data.

    This function:
    1. Loads global item parameters from the server message
    2. Restores local user parameters from context.state (persisted across rounds)
    3. Creates LitBiasedMatrixFactorization and loads merged parameters
    4. Trains locally using PyTorch Lightning Trainer
    5. Saves updated user parameters to context.state
    6. Returns only item-side parameters to server for aggregation

    Args:
        msg: Message from server containing global item parameters
        context: Flower context with node_config, run_config, and state

    Returns:
        Message with updated item parameters and training metrics
    """
    partition_id = int(context.node_config["partition-id"])
    n_factors = context.run_config.get("n-factors", 16)
    local_epochs = context.run_config.get("local-epochs", 1)
    lr = context.run_config.get("lr", 0.02)
    weight_decay = context.run_config.get("weight-decay", 0.005)

    # Setup data
    datamodule = _get_client_datamodule(context)
    num_examples = datamodule.get_num_examples()

    # Create Lightning model
    lit_model = _create_lit_model(
        datamodule,
        n_factors=n_factors,
        lr=lr,
        weight_decay=weight_decay,
    )

    # Load server parameters (item-side)
    server_params = {}
    if "arrays" in msg.content.array_records:
        array_record = msg.content.array_records["arrays"]
        server_params = array_record.to_torch_state_dict()

    # Restore local user parameters from context.state
    local_user_params = None
    if "user_params" in context.state:
        user_record = context.state["user_params"]
        local_user_params = user_record.to_torch_state_dict()

    # Merge parameters and load into model
    merged_state_dict = _merge_parameters(server_params, local_user_params, lit_model)
    _set_inner_state_dict(lit_model, merged_state_dict)

    # Train locally using Lightning Trainer
    trainer = L.Trainer(
        max_epochs=local_epochs,
        enable_progress_bar=False,
        enable_model_summary=False,
        logger=False,
        enable_checkpointing=False,
        accelerator="auto",
        devices=1,
    )
    trainer.fit(lit_model, datamodule=datamodule)

    # Get training loss from logged metrics
    avg_train_loss = trainer.callback_metrics.get("train_loss", torch.tensor(0.0)).item()

    # Get updated state_dict from inner model
    updated_state_dict = _get_inner_state_dict(lit_model)

    # Save user parameters to context.state for next round
    user_params = _extract_user_params(updated_state_dict)
    context.state["user_params"] = ArrayRecord(user_params)

    # Extract only item parameters to send back to server
    item_params = _extract_item_params(updated_state_dict)
    item_record = ArrayRecord(item_params)

    # Prepare metrics
    metrics = MetricRecord({
        "train_loss": avg_train_loss,
        "num-examples": num_examples,
        "partition_id": partition_id,
        "local_epochs": local_epochs,
    })

    # Construct reply message
    content = RecordDict({
        "arrays": item_record,
        "metrics": metrics,
    })

    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context) -> Message:
    """Evaluate the model on local validation data.

    This function:
    1. Loads global item parameters from the server message
    2. Restores local user parameters from context.state
    3. Creates LitBiasedMatrixFactorization and loads merged parameters
    4. Evaluates on validation set using Lightning Trainer
    5. Returns evaluation metrics

    Args:
        msg: Message from server containing global item parameters
        context: Flower context with node_config, run_config, and state

    Returns:
        Message with evaluation metrics (loss, RMSE, MAE)
    """
    partition_id = int(context.node_config["partition-id"])
    n_factors = context.run_config.get("n-factors", 16)
    lr = context.run_config.get("lr", 0.02)
    weight_decay = context.run_config.get("weight-decay", 0.005)

    # Setup data
    datamodule = _get_client_datamodule(context)
    num_examples = len(datamodule.val_dataset) if datamodule.val_dataset else 0

    # Create Lightning model
    lit_model = _create_lit_model(
        datamodule,
        n_factors=n_factors,
        lr=lr,
        weight_decay=weight_decay,
    )

    # Load server parameters (item-side)
    server_params = {}
    if "arrays" in msg.content.array_records:
        array_record = msg.content.array_records["arrays"]
        server_params = array_record.to_torch_state_dict()

    # Restore local user parameters from context.state
    local_user_params = None
    if "user_params" in context.state:
        user_record = context.state["user_params"]
        local_user_params = user_record.to_torch_state_dict()

    # Merge parameters and load into model
    merged_state_dict = _merge_parameters(server_params, local_user_params, lit_model)
    _set_inner_state_dict(lit_model, merged_state_dict)

    # Evaluate using Lightning Trainer
    trainer = L.Trainer(
        enable_progress_bar=False,
        enable_model_summary=False,
        logger=False,
        accelerator="auto",
        devices=1,
    )
    trainer.validate(lit_model, datamodule=datamodule, verbose=False)

    # Get metrics from trainer
    val_rmse = trainer.callback_metrics.get("val_rmse", torch.tensor(0.0)).item()
    val_mae = trainer.callback_metrics.get("val_mae", torch.tensor(0.0)).item()
    mse = val_rmse ** 2  # Convert RMSE back to MSE for loss

    # Prepare metrics
    metrics = MetricRecord({
        "eval_loss": mse,
        "eval_rmse": val_rmse,
        "eval_mae": val_mae,
        "num-examples": num_examples,
        "partition_id": partition_id,
    })

    # Construct reply message (evaluation returns only metrics, no arrays)
    content = RecordDict({
        "metrics": metrics,
    })

    return Message(content=content, reply_to=msg)