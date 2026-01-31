"""Federated learning components using Flower framework.

This module contains all Flower-specific implementations for federated
matrix factorization training, including client logic, server strategy,
and simulation orchestration.
"""

# Shared constants for item-side parameter names
# These parameters are aggregated server-side in federated learning,
# while user-side parameters remain local to each client
ITEM_PARAM_NAMES = frozenset({
    "global_bias",
    "item_bias.weight",
    "item_embedding.weight",
})





