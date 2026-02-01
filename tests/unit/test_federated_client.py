"""Unit tests for federated client_app.py helper functions.

Tests cover:
- Parameter constants (USER_PARAM_NAMES, ITEM_PARAM_NAMES)
- State dict manipulation (_get_inner_state_dict, _set_inner_state_dict)
- Parameter merging and extraction
- Model creation helpers
"""

from collections import OrderedDict

import pytest
import torch

from app.application.federated import ITEM_PARAM_NAMES
from app.application.federated.client_app import (
    USER_PARAM_NAMES,
    _extract_item_params,
    _extract_user_params,
    _get_inner_state_dict,
    _merge_parameters,
    _set_inner_state_dict,
)
from app.application.training.centralized_trainer import LitBiasedMatrixFactorization


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def small_lit_model() -> LitBiasedMatrixFactorization:
    """Create a small LitBiasedMatrixFactorization for testing."""
    return LitBiasedMatrixFactorization(
        n_users=10,
        n_items=20,
        n_factors=4,
        global_mean=3.5,
        learning_rate=0.02,
        regularization=0.005,
    )


@pytest.fixture
def sample_state_dict(small_lit_model: LitBiasedMatrixFactorization) -> OrderedDict:
    """Complete state_dict from the inner model."""
    return _get_inner_state_dict(small_lit_model)


@pytest.fixture
def mock_server_params(small_lit_model: LitBiasedMatrixFactorization) -> dict:
    """Mock server parameters (item-side only) with modified values."""
    state_dict = _get_inner_state_dict(small_lit_model)
    return {
        "global_bias": state_dict["global_bias"] + 0.5,
        "item_bias.weight": state_dict["item_bias.weight"] + 0.1,
        "item_embedding.weight": state_dict["item_embedding.weight"] + 0.1,
    }


@pytest.fixture
def mock_user_params(small_lit_model: LitBiasedMatrixFactorization) -> dict:
    """Mock local user parameters with modified values."""
    state_dict = _get_inner_state_dict(small_lit_model)
    return {
        "user_bias.weight": state_dict["user_bias.weight"] + 0.2,
        "user_embedding.weight": state_dict["user_embedding.weight"] + 0.2,
    }


# -----------------------------------------------------------------------------
# Constants Tests
# -----------------------------------------------------------------------------


class TestParameterConstants:
    """Tests for USER_PARAM_NAMES and ITEM_PARAM_NAMES constants."""

    def test_user_param_names_contains_expected_keys(self) -> None:
        """USER_PARAM_NAMES contains user embedding and bias."""
        assert "user_bias.weight" in USER_PARAM_NAMES
        assert "user_embedding.weight" in USER_PARAM_NAMES
        assert len(USER_PARAM_NAMES) == 2

    def test_item_param_names_contains_expected_keys(self) -> None:
        """ITEM_PARAM_NAMES contains item embedding, bias, and global bias."""
        assert "global_bias" in ITEM_PARAM_NAMES
        assert "item_bias.weight" in ITEM_PARAM_NAMES
        assert "item_embedding.weight" in ITEM_PARAM_NAMES
        assert len(ITEM_PARAM_NAMES) == 3

    def test_no_overlap_between_user_and_item_params(self) -> None:
        """USER_PARAM_NAMES and ITEM_PARAM_NAMES have no overlap."""
        overlap = USER_PARAM_NAMES & ITEM_PARAM_NAMES
        assert len(overlap) == 0

    def test_all_params_cover_model_state(
        self, sample_state_dict: OrderedDict
    ) -> None:
        """USER_PARAM_NAMES + ITEM_PARAM_NAMES cover all model params."""
        all_params = USER_PARAM_NAMES | ITEM_PARAM_NAMES
        model_params = set(sample_state_dict.keys())
        assert all_params == model_params


# -----------------------------------------------------------------------------
# _get_inner_state_dict Tests
# -----------------------------------------------------------------------------


class TestGetInnerStateDict:
    """Tests for _get_inner_state_dict function."""

    def test_returns_ordered_dict(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Returns an OrderedDict."""
        state_dict = _get_inner_state_dict(small_lit_model)
        assert isinstance(state_dict, OrderedDict)

    def test_contains_expected_keys(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """State dict contains all expected parameter keys."""
        state_dict = _get_inner_state_dict(small_lit_model)
        expected_keys = {
            "global_bias",
            "user_embedding.weight",
            "user_bias.weight",
            "item_embedding.weight",
            "item_bias.weight",
        }
        assert set(state_dict.keys()) == expected_keys

    def test_no_model_prefix_in_keys(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Keys do not have 'model.' prefix (inner model state)."""
        state_dict = _get_inner_state_dict(small_lit_model)
        for key in state_dict.keys():
            assert not key.startswith("model.")

    def test_parameter_shapes_match_model_dimensions(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Parameter tensors have correct shapes."""
        state_dict = _get_inner_state_dict(small_lit_model)
        # n_users=10, n_items=20, n_factors=4
        assert state_dict["global_bias"].shape == ()
        assert state_dict["user_embedding.weight"].shape == (10, 4)
        assert state_dict["user_bias.weight"].shape == (10, 1)
        assert state_dict["item_embedding.weight"].shape == (20, 4)
        assert state_dict["item_bias.weight"].shape == (20, 1)


# -----------------------------------------------------------------------------
# _set_inner_state_dict Tests
# -----------------------------------------------------------------------------


class TestSetInnerStateDict:
    """Tests for _set_inner_state_dict function."""

    def test_loads_parameters_into_model(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Parameters are loaded into the inner model."""
        # Clone original state to avoid reference bug (state_dict returns live refs)
        original_state = OrderedDict()
        for key, value in _get_inner_state_dict(small_lit_model).items():
            original_state[key] = value.clone()

        # Create modified state dict
        modified_state = OrderedDict()
        for key, value in original_state.items():
            modified_state[key] = value + 1.0

        # Load modified state
        _set_inner_state_dict(small_lit_model, modified_state)

        # Verify parameters changed
        new_state = _get_inner_state_dict(small_lit_model)
        for key in original_state.keys():
            assert torch.allclose(new_state[key], original_state[key] + 1.0)

    def test_model_produces_different_output_after_load(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Model predictions change after loading new parameters."""
        users = torch.tensor([0, 1, 2])
        items = torch.tensor([0, 1, 2])

        # Get original predictions
        original_preds = small_lit_model(users, items).clone()

        # Modify and load new parameters
        original_state = _get_inner_state_dict(small_lit_model)
        modified_state = OrderedDict()
        for key, value in original_state.items():
            modified_state[key] = value + 5.0

        _set_inner_state_dict(small_lit_model, modified_state)

        # Get new predictions
        new_preds = small_lit_model(users, items)

        # Predictions should be different
        assert not torch.allclose(original_preds, new_preds)


# -----------------------------------------------------------------------------
# _merge_parameters Tests
# -----------------------------------------------------------------------------


class TestMergeParameters:
    """Tests for _merge_parameters function."""

    def test_merges_server_and_local_params(
        self,
        small_lit_model: LitBiasedMatrixFactorization,
        mock_server_params: dict,
        mock_user_params: dict,
    ) -> None:
        """Correctly merges server and local user parameters."""
        merged = _merge_parameters(mock_server_params, mock_user_params, small_lit_model)

        # All keys should be present
        assert set(merged.keys()) == USER_PARAM_NAMES | ITEM_PARAM_NAMES

        # Server params should be applied to item-side
        assert torch.allclose(merged["global_bias"], mock_server_params["global_bias"])
        assert torch.allclose(
            merged["item_bias.weight"], mock_server_params["item_bias.weight"]
        )

        # Local params should be applied to user-side
        assert torch.allclose(
            merged["user_bias.weight"], mock_user_params["user_bias.weight"]
        )

    def test_server_params_override_model_defaults_for_items(
        self,
        small_lit_model: LitBiasedMatrixFactorization,
        mock_server_params: dict,
    ) -> None:
        """Server params override model defaults for item-side params."""
        original_state = _get_inner_state_dict(small_lit_model)
        merged = _merge_parameters(mock_server_params, None, small_lit_model)

        # Item params should match server params
        assert torch.allclose(merged["global_bias"], mock_server_params["global_bias"])

        # User params should be from model defaults (unchanged)
        assert torch.allclose(
            merged["user_embedding.weight"], original_state["user_embedding.weight"]
        )

    def test_local_user_params_override_model_defaults(
        self,
        small_lit_model: LitBiasedMatrixFactorization,
        mock_user_params: dict,
    ) -> None:
        """Local user params override model defaults for user-side params."""
        original_state = _get_inner_state_dict(small_lit_model)
        # No server params, only local user params
        merged = _merge_parameters({}, mock_user_params, small_lit_model)

        # User params should match local params
        assert torch.allclose(
            merged["user_bias.weight"], mock_user_params["user_bias.weight"]
        )

        # Item params should be from model defaults (unchanged)
        assert torch.allclose(
            merged["item_embedding.weight"], original_state["item_embedding.weight"]
        )

    def test_handles_none_local_user_params(
        self,
        small_lit_model: LitBiasedMatrixFactorization,
        mock_server_params: dict,
    ) -> None:
        """Handles None local_user_params (first round scenario)."""
        original_state = _get_inner_state_dict(small_lit_model)

        # Should not raise, should use model defaults for user params
        merged = _merge_parameters(mock_server_params, None, small_lit_model)

        # User params should be from model defaults
        assert torch.allclose(
            merged["user_embedding.weight"], original_state["user_embedding.weight"]
        )

    def test_returns_ordered_dict(
        self,
        small_lit_model: LitBiasedMatrixFactorization,
        mock_server_params: dict,
    ) -> None:
        """Returns an OrderedDict."""
        merged = _merge_parameters(mock_server_params, None, small_lit_model)
        assert isinstance(merged, OrderedDict)


# -----------------------------------------------------------------------------
# _extract_item_params Tests
# -----------------------------------------------------------------------------


class TestExtractItemParams:
    """Tests for _extract_item_params function."""

    def test_extracts_only_item_side_params(
        self, sample_state_dict: OrderedDict
    ) -> None:
        """Extracts only item-side parameters."""
        item_params = _extract_item_params(sample_state_dict)
        assert set(item_params.keys()) == ITEM_PARAM_NAMES

    def test_returns_correct_subset(
        self, sample_state_dict: OrderedDict
    ) -> None:
        """Values match original state dict."""
        item_params = _extract_item_params(sample_state_dict)
        assert torch.equal(item_params["global_bias"], sample_state_dict["global_bias"])
        assert torch.equal(
            item_params["item_embedding.weight"],
            sample_state_dict["item_embedding.weight"],
        )
        assert torch.equal(
            item_params["item_bias.weight"], sample_state_dict["item_bias.weight"]
        )

    def test_returns_empty_if_no_item_params(self) -> None:
        """Returns empty dict if no item params present."""
        user_only = {"user_embedding.weight": torch.randn(10, 4)}
        item_params = _extract_item_params(user_only)
        assert len(item_params) == 0

    def test_returns_ordered_dict(self, sample_state_dict: OrderedDict) -> None:
        """Returns an OrderedDict."""
        item_params = _extract_item_params(sample_state_dict)
        assert isinstance(item_params, OrderedDict)


# -----------------------------------------------------------------------------
# _extract_user_params Tests
# -----------------------------------------------------------------------------


class TestExtractUserParams:
    """Tests for _extract_user_params function."""

    def test_extracts_only_user_side_params(
        self, sample_state_dict: OrderedDict
    ) -> None:
        """Extracts only user-side parameters."""
        user_params = _extract_user_params(sample_state_dict)
        assert set(user_params.keys()) == USER_PARAM_NAMES

    def test_returns_correct_subset(
        self, sample_state_dict: OrderedDict
    ) -> None:
        """Values match original state dict."""
        user_params = _extract_user_params(sample_state_dict)
        assert torch.equal(
            user_params["user_embedding.weight"],
            sample_state_dict["user_embedding.weight"],
        )
        assert torch.equal(
            user_params["user_bias.weight"], sample_state_dict["user_bias.weight"]
        )

    def test_returns_empty_if_no_user_params(self) -> None:
        """Returns empty dict if no user params present."""
        item_only = {"global_bias": torch.tensor(3.5)}
        user_params = _extract_user_params(item_only)
        assert len(user_params) == 0

    def test_returns_ordered_dict(self, sample_state_dict: OrderedDict) -> None:
        """Returns an OrderedDict."""
        user_params = _extract_user_params(sample_state_dict)
        assert isinstance(user_params, OrderedDict)


# -----------------------------------------------------------------------------
# Parameter Round-Trip Tests
# -----------------------------------------------------------------------------


class TestParameterRoundTrip:
    """Integration tests for parameter extraction and merging."""

    def test_extract_merge_round_trip(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Extracted params can be merged back correctly."""
        original_state = _get_inner_state_dict(small_lit_model)

        # Extract both sides
        item_params = _extract_item_params(original_state)
        user_params = _extract_user_params(original_state)

        # Merge back
        merged = _merge_parameters(item_params, user_params, small_lit_model)

        # Should match original
        for key in original_state.keys():
            assert torch.allclose(merged[key], original_state[key])

    def test_item_params_are_server_compatible(
        self, small_lit_model: LitBiasedMatrixFactorization
    ) -> None:
        """Extracted item params can simulate server aggregation."""
        state_dict = _get_inner_state_dict(small_lit_model)
        item_params = _extract_item_params(state_dict)

        # Simulate averaging with itself (identity)
        averaged = OrderedDict()
        for key, value in item_params.items():
            averaged[key] = value.clone()

        # Can be merged back into a model
        merged = _merge_parameters(averaged, None, small_lit_model)
        assert set(merged.keys()) == USER_PARAM_NAMES | ITEM_PARAM_NAMES
