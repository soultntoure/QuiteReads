"""
Custom Federated Aggregation Strategy.

Implements FedAvgItemsOnly: aggregates only item-side parameters
(item embeddings, item biases, global bias) while keeping user embeddings local.

This implementation uses Flower's Message API with name-based parameter filtering.
"""

from collections import OrderedDict
from logging import WARNING
from typing import Iterable

from flwr.app import ArrayRecord, Message, MetricRecord
from flwr.common.logger import log
from flwr.serverapp.strategy import FedAvg


class FedAvgItemsOnly(FedAvg):
    """Federated Averaging strategy that aggregates only item-side parameters.

    This strategy extends FedAvg to handle the unique requirements of federated
    Matrix Factorization, where user embeddings are client-specific and should
    NOT be aggregated across clients.

    ## Why This Strategy Exists

    In federated recommender systems using Matrix Factorization:
    - **User embeddings are client-specific**: User k on Client A is NOT the same
      as user k on Client B. Averaging these embeddings is semantically meaningless
      and destroys model performance.
    - **Item embeddings are global**: All clients share the same item catalog, so
      item embeddings should be aggregated via FedAvg.

    ## What Gets Aggregated

    This strategy performs weighted averaging on:
    - `global_bias`: Global mean rating (single parameter)
    - `item_embedding.weight`: Item latent factors (n_items × n_factors)
    - `item_bias.weight`: Item bias terms (n_items × 1)

    User embeddings (`user_embedding.weight`, `user_bias.weight`) remain local
    to each client and are never aggregated.

    ## Name-Based Filtering

    Uses Flower's Message API with ArrayRecord for robust name-based filtering:
    - ✅ No dependency on parameter ordering
    - ✅ Explicit parameter names (self-documenting)
    - ✅ Catches errors if parameter names don't match
    - ✅ Works with Flower 1.25+ Message API

    Parameters filtered by name:
        - "global_bias"
        - "item_bias.weight"
        - "item_embedding.weight"

    ## Usage Example

    ```python
    from src.federated.strategy import FedAvgItemsOnly

    # Default: aggregates the three item-side parameters
    strategy = FedAvgItemsOnly(
        fraction_fit=1.0,
        min_fit_clients=2,
    )

    # Custom parameter names (if your model structure differs)
    strategy = FedAvgItemsOnly(
        fraction_fit=1.0,
        min_fit_clients=2,
        item_param_names=["global_bias", "item_bias.weight", "item_embedding.weight"],
    )
    ```

    """

    def __init__(
        self,
        *,
        item_param_names: list[str] | None = None,
        **kwargs,
    ):
        """Initialize FedAvgItemsOnly strategy.

        Args:
            item_param_names: Names of item-side parameters to aggregate.
                Default: ["global_bias", "item_bias.weight", "item_embedding.weight"]
            **kwargs: Arguments passed to FedAvg (including weighted_by_key,
                train_metrics_aggr_fn, fraction_fit, min_fit_clients, etc.)
        """
        # Configurable parameter names for name-based filtering
        self.item_param_names = item_param_names or [
            "global_bias",
            "item_bias.weight",
            "item_embedding.weight",
        ]

        # Extract and map custom terminology to FedAvg expected arguments
        # We store weighted_by_key for use in aggregate_train
        self.weighted_by_key = kwargs.get("weighted_by_key", "num-examples")

        super().__init__(**kwargs)

        log(
            WARNING,
            "FedAvgItemsOnly initialized with name-based filtering: %s",
            self.item_param_names,
        )

    def aggregate_train(
        self,
        server_round: int,
        replies: Iterable[Message],
    ) -> tuple[ArrayRecord | None, MetricRecord | None]:
        """Aggregate training results using name-based filtering (Message API).

        This method implements name-based parameter filtering using Flower's
        Message API with ArrayRecord. It explicitly filters by parameter names
        rather than relying on parameter ordering.

        This method:
        1. Extracts ArrayRecords from client messages
        2. Converts each ArrayRecord to PyTorch state_dict (preserves names!)
        3. Filters to keep only item-side parameters by name
        4. Performs weighted averaging using num-examples as weight
        5. Returns aggregated item-side parameters and metrics

        Args:
            server_round: Current federated round number
            replies: Iterator of Message objects from clients

        Returns:
            Tuple of:
                - Aggregated ArrayRecord (item-side params only), or None if failed
                - Aggregated MetricRecord, or None if failed

        Example:
            ```python
            # In ServerApp with Message API
            strategy = FedAvgItemsOnly(
                item_param_names=["global_bias", "item_bias.weight", "item_embedding.weight"]
            )

            # aggregate_train will filter by these names automatically
            ```
        """
        # Convert iterator to list and filter out error messages
        replies_list = [msg for msg in replies if not msg.has_error()]

        if not replies_list:
            log(WARNING, "aggregate_train: No valid replies to aggregate")
            return None, None

        # Extract array record key (assumes all clients use the same key)
        first_content = replies_list[0].content
        array_record_key = next(iter(first_content.array_records.keys()))

        # Collect state_dicts and weights from all clients
        state_dicts_and_weights: list[tuple[OrderedDict, int]] = []

        for msg in replies_list:
            content = msg.content
            array_record = content.array_records[array_record_key]

            # Convert ArrayRecord to state_dict (preserves parameter names!)
            state_dict = array_record.to_torch_state_dict()

            # Extract num-examples from metrics for weighted averaging
            metrics = content.metric_records.get("metrics", {})
            num_examples = metrics.get(self.weighted_by_key, 1)

            state_dicts_and_weights.append((state_dict, num_examples))

        # Validate that all clients sent consistent parameters
        param_names_per_client = [set(sd.keys()) for sd, _ in state_dicts_and_weights]
        if len(set(frozenset(names) for names in param_names_per_client)) > 1:
            log(
                WARNING,
                "aggregate_train: Inconsistent parameter names across clients: %s",
                param_names_per_client,
            )
            return None, None

        # Filter to keep only item-side parameters by name
        item_state_dicts_and_weights = [
            (
                OrderedDict({k: v for k, v in state_dict.items() if k in self.item_param_names}),
                num_examples,
            )
            for state_dict, num_examples in state_dicts_and_weights
        ]

        # Check if filtering was successful
        first_filtered = item_state_dicts_and_weights[0][0]
        if len(first_filtered) == 0:
            log(
                WARNING,
                "aggregate_train: No parameters matched filter names %s. "
                "Available parameters: %s",
                self.item_param_names,
                list(state_dicts_and_weights[0][0].keys()),
            )
            return None, None

        log(
            WARNING,
            "aggregate_train round %d: Filtering %d→%d item-side parameters from %d clients\n"
            "  Kept: %s",
            server_round,
            len(state_dicts_and_weights[0][0]),
            len(first_filtered),
            len(replies_list),
            list(first_filtered.keys()),
        )

        # Perform weighted averaging
        aggregated_state_dict = self._weighted_average_state_dicts(
            item_state_dicts_and_weights
        )

        # Convert back to ArrayRecord
        aggregated_array_record = ArrayRecord(aggregated_state_dict)

        # Aggregate metrics
        if self.train_metrics_aggr_fn:
            metrics_aggregated = self.train_metrics_aggr_fn(
                [msg.content for msg in replies_list],
                self.weighted_by_key,
            )
        else:
            metrics_aggregated = {}

        return aggregated_array_record, metrics_aggregated

    def _weighted_average_state_dicts(
        self,
        state_dicts_and_weights: list[tuple[OrderedDict, int]],
    ) -> OrderedDict:
        """Compute weighted average of state dicts.

        Args:
            state_dicts_and_weights: List of (state_dict, num_examples) tuples

        Returns:
            Aggregated state_dict with weighted averaged parameters
        """
        # Get parameter names from first state dict
        param_names = list(state_dicts_and_weights[0][0].keys())

        # Compute total weight
        total_weight = sum(weight for _, weight in state_dicts_and_weights)

        # Initialize aggregated state dict
        aggregated = OrderedDict()

        # Weighted average for each parameter
        for param_name in param_names:
            weighted_sum = sum(
                state_dict[param_name] * weight
                for state_dict, weight in state_dicts_and_weights
            )
            aggregated[param_name] = weighted_sum / total_weight

        return aggregated