"""Federated learning components using Flower framework.

This module contains all Flower-specific implementations for federated
matrix factorization training, including client logic, server strategy,
and simulation orchestration.
"""

from typing import Any, Dict

# Shared constants for item-side parameter names
# These parameters are aggregated server-side in federated learning,
# while user-side parameters remain local to each client
ITEM_PARAM_NAMES = frozenset({
    "global_bias",
    "item_bias.weight",
    "item_embedding.weight",
})

# Module-level run configuration shared between simulation manager and Flower apps.
# Flower 1.25's run_simulation() does not accept a run_config parameter;
# context.run_config is empty when invoked programmatically.
# FederatedSimulationManager populates this before calling run_simulation(),
# and server_app / client_app read from it as a fallback.
_simulation_run_config: Dict[str, Any] = {}


def get_run_config(context_run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Return effective run config, preferring context over shared fallback."""
    if context_run_config:
        return context_run_config
    return _simulation_run_config





