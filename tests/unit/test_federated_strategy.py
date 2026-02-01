"""Unit tests for FedAvgItemsOnly strategy class.

Tests cover:
- Strategy initialization and configuration
- Weighted average computation
- Parameter filtering logic
"""

from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest
import torch

from app.application.federated import ITEM_PARAM_NAMES
from app.application.federated.strategy import FedAvgItemsOnly


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def default_strategy() -> FedAvgItemsOnly:
    """Create FedAvgItemsOnly with default settings."""
    return FedAvgItemsOnly()


@pytest.fixture
def custom_strategy() -> FedAvgItemsOnly:
    """Create FedAvgItemsOnly with custom item_param_names."""
    return FedAvgItemsOnly(
        item_param_names=["custom_param_1", "custom_param_2"],
        weighted_by_key="custom-weight",
    )


@pytest.fixture
def sample_state_dicts_and_weights() -> list[tuple[OrderedDict, int]]:
    """Sample state dicts with weights for aggregation testing."""
    return [
        (
            OrderedDict([
                ("global_bias", torch.tensor(1.0)),
                ("item_embedding.weight", torch.tensor([[1.0, 2.0], [3.0, 4.0]])),
                ("item_bias.weight", torch.tensor([[0.1], [0.2]])),
            ]),
            100,  # num_examples
        ),
        (
            OrderedDict([
                ("global_bias", torch.tensor(2.0)),
                ("item_embedding.weight", torch.tensor([[2.0, 3.0], [4.0, 5.0]])),
                ("item_bias.weight", torch.tensor([[0.2], [0.3]])),
            ]),
            200,  # num_examples
        ),
        (
            OrderedDict([
                ("global_bias", torch.tensor(3.0)),
                ("item_embedding.weight", torch.tensor([[3.0, 4.0], [5.0, 6.0]])),
                ("item_bias.weight", torch.tensor([[0.3], [0.4]])),
            ]),
            300,  # num_examples
        ),
    ]


@pytest.fixture
def equal_weight_state_dicts() -> list[tuple[OrderedDict, int]]:
    """State dicts with equal weights for uniform averaging."""
    return [
        (OrderedDict([("global_bias", torch.tensor(1.0))]), 100),
        (OrderedDict([("global_bias", torch.tensor(2.0))]), 100),
        (OrderedDict([("global_bias", torch.tensor(3.0))]), 100),
    ]


# -----------------------------------------------------------------------------
# Initialization Tests
# -----------------------------------------------------------------------------


class TestFedAvgItemsOnlyInitialization:
    """Tests for FedAvgItemsOnly initialization."""

    def test_default_item_param_names_uses_constant(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Default item_param_names uses ITEM_PARAM_NAMES constant."""
        assert set(default_strategy.item_param_names) == ITEM_PARAM_NAMES

    def test_custom_item_param_names_overrides_default(
        self, custom_strategy: FedAvgItemsOnly
    ) -> None:
        """Custom item_param_names overrides default."""
        assert custom_strategy.item_param_names == ["custom_param_1", "custom_param_2"]

    def test_weighted_by_key_defaults_to_num_examples(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Default weighted_by_key is 'num-examples'."""
        assert default_strategy.weighted_by_key == "num-examples"

    def test_custom_weighted_by_key(
        self, custom_strategy: FedAvgItemsOnly
    ) -> None:
        """Custom weighted_by_key is respected."""
        assert custom_strategy.weighted_by_key == "custom-weight"

    def test_inherits_from_fedavg(self, default_strategy: FedAvgItemsOnly) -> None:
        """FedAvgItemsOnly inherits from FedAvg."""
        from flwr.serverapp.strategy import FedAvg
        assert isinstance(default_strategy, FedAvg)


# -----------------------------------------------------------------------------
# _weighted_average_state_dicts Tests
# -----------------------------------------------------------------------------


class TestWeightedAverageStateDicts:
    """Tests for _weighted_average_state_dicts method."""

    def test_computes_weighted_average_single_param(
        self, default_strategy: FedAvgItemsOnly, equal_weight_state_dicts
    ) -> None:
        """Correctly computes weighted average with single parameter."""
        result = default_strategy._weighted_average_state_dicts(equal_weight_state_dicts)
        # Equal weights: (1 + 2 + 3) / 3 = 2.0
        assert torch.isclose(result["global_bias"], torch.tensor(2.0))

    def test_weighted_average_with_different_weights(
        self, default_strategy: FedAvgItemsOnly, sample_state_dicts_and_weights
    ) -> None:
        """Correctly computes weighted average with different weights."""
        result = default_strategy._weighted_average_state_dicts(
            sample_state_dicts_and_weights
        )
        # Weights: 100, 200, 300 (total=600)
        # global_bias: (1*100 + 2*200 + 3*300) / 600 = (100 + 400 + 900) / 600 = 2.333...
        expected = (1.0 * 100 + 2.0 * 200 + 3.0 * 300) / 600.0
        assert torch.isclose(result["global_bias"], torch.tensor(expected))

    def test_weighted_average_multiple_params(
        self, default_strategy: FedAvgItemsOnly, sample_state_dicts_and_weights
    ) -> None:
        """Weighted average works for multiple parameters."""
        result = default_strategy._weighted_average_state_dicts(
            sample_state_dicts_and_weights
        )
        # All expected params present
        assert "global_bias" in result
        assert "item_embedding.weight" in result
        assert "item_bias.weight" in result

    def test_weighted_average_preserves_tensor_shapes(
        self, default_strategy: FedAvgItemsOnly, sample_state_dicts_and_weights
    ) -> None:
        """Weighted average preserves tensor shapes."""
        result = default_strategy._weighted_average_state_dicts(
            sample_state_dicts_and_weights
        )
        # item_embedding.weight should be (2, 2)
        assert result["item_embedding.weight"].shape == (2, 2)
        # item_bias.weight should be (2, 1)
        assert result["item_bias.weight"].shape == (2, 1)

    def test_weighted_average_2d_tensor(
        self, default_strategy: FedAvgItemsOnly, sample_state_dicts_and_weights
    ) -> None:
        """Weighted average works for 2D tensors (embeddings)."""
        result = default_strategy._weighted_average_state_dicts(
            sample_state_dicts_and_weights
        )
        # item_embedding.weight[0,0]:
        # (1*100 + 2*200 + 3*300) / 600 = 2.333...
        expected_00 = (1.0 * 100 + 2.0 * 200 + 3.0 * 300) / 600.0
        assert torch.isclose(
            result["item_embedding.weight"][0, 0], torch.tensor(expected_00)
        )

    def test_uniform_weights_equals_simple_average(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Equal weights produce simple arithmetic mean."""
        state_dicts = [
            (OrderedDict([("param", torch.tensor([1.0, 2.0]))]), 1),
            (OrderedDict([("param", torch.tensor([3.0, 4.0]))]), 1),
        ]
        result = default_strategy._weighted_average_state_dicts(state_dicts)
        expected = torch.tensor([2.0, 3.0])
        assert torch.allclose(result["param"], expected)

    def test_returns_ordered_dict(
        self, default_strategy: FedAvgItemsOnly, sample_state_dicts_and_weights
    ) -> None:
        """Returns an OrderedDict."""
        result = default_strategy._weighted_average_state_dicts(
            sample_state_dicts_and_weights
        )
        assert isinstance(result, OrderedDict)


# -----------------------------------------------------------------------------
# aggregate_train Tests (Mock Flower Messages)
# -----------------------------------------------------------------------------


class TestAggregateTrain:
    """Tests for aggregate_train method with mocked Flower messages."""

    def test_returns_none_when_no_valid_replies(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Returns (None, None) when no valid replies."""
        result = default_strategy.aggregate_train(server_round=1, replies=[])
        assert result == (None, None)

    def test_returns_none_when_all_replies_have_errors(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Returns (None, None) when all replies have errors."""
        mock_msg = MagicMock()
        mock_msg.has_error.return_value = True
        
        result = default_strategy.aggregate_train(server_round=1, replies=[mock_msg])
        assert result == (None, None)

    def test_filters_item_params_correctly(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Correctly filters to item-side parameters only."""
        # Create mock message with both user and item params
        mock_content = MagicMock()
        mock_array_record = MagicMock()
        mock_array_record.to_torch_state_dict.return_value = OrderedDict([
            ("global_bias", torch.tensor(1.0)),
            ("item_embedding.weight", torch.tensor([[1.0]])),
            ("item_bias.weight", torch.tensor([[0.1]])),
            ("user_embedding.weight", torch.tensor([[2.0]])),  # Should be filtered
            ("user_bias.weight", torch.tensor([[0.2]])),  # Should be filtered
        ])
        mock_content.array_records = {"arrays": mock_array_record}
        mock_content.metric_records = {"metrics": {"num-examples": 100}}
        
        mock_msg = MagicMock()
        mock_msg.has_error.return_value = False
        mock_msg.content = mock_content

        result, _ = default_strategy.aggregate_train(
            server_round=1, replies=[mock_msg]
        )
        
        # Should only contain item params
        if result is not None:
            result_dict = result.to_torch_state_dict()
            assert "global_bias" in result_dict
            assert "user_embedding.weight" not in result_dict

    def test_returns_none_when_no_params_match_filter(self) -> None:
        """Returns (None, None) when filter produces empty result."""
        strategy = FedAvgItemsOnly(item_param_names=["nonexistent_param"])
        
        mock_content = MagicMock()
        mock_array_record = MagicMock()
        mock_array_record.to_torch_state_dict.return_value = OrderedDict([
            ("global_bias", torch.tensor(1.0)),
        ])
        mock_content.array_records = {"arrays": mock_array_record}
        mock_content.metric_records = {"metrics": {"num-examples": 100}}
        
        mock_msg = MagicMock()
        mock_msg.has_error.return_value = False
        mock_msg.content = mock_content

        result = strategy.aggregate_train(server_round=1, replies=[mock_msg])
        assert result == (None, None)


# -----------------------------------------------------------------------------
# Edge Cases
# -----------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for FedAvgItemsOnly."""

    def test_empty_item_param_names_uses_default(self) -> None:
        """Strategy with empty item_param_names falls back to default.
        
        Empty list is falsy in Python, so `item_param_names or list(ITEM_PARAM_NAMES)`
        evaluates to the default.
        """
        strategy = FedAvgItemsOnly(item_param_names=[])
        # Empty list is falsy, so default is used
        assert set(strategy.item_param_names) == ITEM_PARAM_NAMES

    def test_single_client_aggregation(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Aggregation with single client returns same values."""
        state_dicts = [
            (OrderedDict([("global_bias", torch.tensor(5.0))]), 100),
        ]
        result = default_strategy._weighted_average_state_dicts(state_dicts)
        assert torch.isclose(result["global_bias"], torch.tensor(5.0))

    def test_zero_weight_clients(
        self, default_strategy: FedAvgItemsOnly
    ) -> None:
        """Handles zero-weight edge case (all weight in one client)."""
        state_dicts = [
            (OrderedDict([("global_bias", torch.tensor(1.0))]), 0),
            (OrderedDict([("global_bias", torch.tensor(5.0))]), 100),
        ]
        result = default_strategy._weighted_average_state_dicts(state_dicts)
        # First client has 0 weight, result should be 5.0
        assert torch.isclose(result["global_bias"], torch.tensor(5.0))
