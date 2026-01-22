"""Unit tests for BiasedMatrixFactorization model.

Tests cover:
- Model initialization and parameter setup
- Forward pass and prediction generation
- Gradient computation (backward pass)
- Configuration and parameter counting methods
"""

import pytest
import torch
import torch.nn as nn

from app.core.models.matrix_factorization import BiasedMatrixFactorization


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def small_model() -> BiasedMatrixFactorization:
    """Create small model for basic tests."""
    return BiasedMatrixFactorization(
        n_users=100,
        n_items=50,
        n_factors=10,
        global_mean=4.0,
    )


@pytest.fixture
def large_model() -> BiasedMatrixFactorization:
    """Create larger model for performance tests."""
    return BiasedMatrixFactorization(
        n_users=5949,
        n_items=2856,
        n_factors=50,
        global_mean=4.07,
    )


@pytest.fixture
def batch_inputs() -> tuple[torch.Tensor, torch.Tensor]:
    """Create batch of user-item pairs for testing."""
    batch_size = 32
    user_ids = torch.randint(0, 100, (batch_size,))
    item_ids = torch.randint(0, 50, (batch_size,))
    return user_ids, item_ids


# -----------------------------------------------------------------------------
# Initialization Tests
# -----------------------------------------------------------------------------


class TestModelInitialization:
    """Tests for model initialization."""

    def test_model_attributes_set_correctly(self) -> None:
        """Model attributes are set correctly during initialization."""
        model = BiasedMatrixFactorization(
            n_users=1000,
            n_items=500,
            n_factors=20,
            global_mean=3.5,
        )
        assert model.n_users == 1000
        assert model.n_items == 500
        assert model.n_factors == 20
        assert model.global_bias.item() == pytest.approx(3.5)

    def test_global_bias_is_trainable_parameter(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """Global bias is a trainable nn.Parameter."""
        assert isinstance(small_model.global_bias, nn.Parameter)
        assert small_model.global_bias.requires_grad is True

    def test_embeddings_have_correct_dimensions(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """User and item embeddings have correct dimensions."""
        assert small_model.user_embedding.num_embeddings == 100
        assert small_model.user_embedding.embedding_dim == 10
        assert small_model.item_embedding.num_embeddings == 50
        assert small_model.item_embedding.embedding_dim == 10

    def test_biases_have_correct_dimensions(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """User and item biases have correct dimensions."""
        assert small_model.user_bias.num_embeddings == 100
        assert small_model.user_bias.embedding_dim == 1
        assert small_model.item_bias.num_embeddings == 50
        assert small_model.item_bias.embedding_dim == 1

    def test_embeddings_initialized_with_small_values(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """Embeddings initialized with small random values (normal dist)."""
        # Check that weights are small (std ~0.01)
        user_emb_std = small_model.user_embedding.weight.std().item()
        item_emb_std = small_model.item_embedding.weight.std().item()
        assert user_emb_std < 0.1  # Should be around 0.01
        assert item_emb_std < 0.1

    def test_biases_initialized_to_zero(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """User and item biases initialized to zero."""
        assert torch.allclose(small_model.user_bias.weight, torch.zeros_like(small_model.user_bias.weight))
        assert torch.allclose(small_model.item_bias.weight, torch.zeros_like(small_model.item_bias.weight))

    def test_default_global_mean_is_zero(self) -> None:
        """Default global_mean is 0.0 if not specified."""
        model = BiasedMatrixFactorization(n_users=10, n_items=5, n_factors=3)
        assert model.global_bias.item() == 0.0


# -----------------------------------------------------------------------------
# Forward Pass Tests
# -----------------------------------------------------------------------------


class TestForwardPass:
    """Tests for forward pass computation."""

    def test_forward_returns_correct_shape(
        self,
        small_model: BiasedMatrixFactorization,
        batch_inputs: tuple[torch.Tensor, torch.Tensor],
    ) -> None:
        """Forward pass returns tensor with correct shape."""
        user_ids, item_ids = batch_inputs
        predictions = small_model(user_ids, item_ids)
        assert predictions.shape == (32,)

    def test_forward_single_prediction(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """Forward pass works for single user-item pair."""
        user_ids = torch.tensor([5])
        item_ids = torch.tensor([10])
        predictions = small_model(user_ids, item_ids)
        assert predictions.shape == (1,)

    def test_forward_large_batch(
        self, large_model: BiasedMatrixFactorization
    ) -> None:
        """Forward pass handles large batches efficiently."""
        batch_size = 1024
        user_ids = torch.randint(0, 5949, (batch_size,))
        item_ids = torch.randint(0, 2856, (batch_size,))
        predictions = large_model(user_ids, item_ids)
        assert predictions.shape == (batch_size,)

    def test_predictions_are_floats(
        self,
        small_model: BiasedMatrixFactorization,
        batch_inputs: tuple[torch.Tensor, torch.Tensor],
    ) -> None:
        """Predictions are floating-point values."""
        user_ids, item_ids = batch_inputs
        predictions = small_model(user_ids, item_ids)
        assert predictions.dtype == torch.float32

    def test_predictions_centered_around_global_mean(self) -> None:
        """Predictions centered around global mean initially."""
        model = BiasedMatrixFactorization(
            n_users=100,
            n_items=50,
            n_factors=10,
            global_mean=4.0,
        )
        user_ids = torch.randint(0, 100, (1000,))
        item_ids = torch.randint(0, 50, (1000,))
        predictions = model(user_ids, item_ids)

        # With small initialized embeddings/biases, predictions should be close to global_mean
        mean_prediction = predictions.mean().item()
        assert abs(mean_prediction - 4.0) < 0.5


# -----------------------------------------------------------------------------
# Gradient Computation Tests
# -----------------------------------------------------------------------------


class TestGradientComputation:
    """Tests for backward pass and gradient flow."""

    def test_backward_pass_computes_gradients(
        self,
        small_model: BiasedMatrixFactorization,
        batch_inputs: tuple[torch.Tensor, torch.Tensor],
    ) -> None:
        """Backward pass computes gradients for all parameters."""
        user_ids, item_ids = batch_inputs
        targets = torch.rand(32) * 4 + 1  # Random ratings 1-5

        predictions = small_model(user_ids, item_ids)
        loss = nn.MSELoss()(predictions, targets)
        loss.backward()

        # Check all parameters have gradients
        assert small_model.global_bias.grad is not None
        assert small_model.user_embedding.weight.grad is not None
        assert small_model.item_embedding.weight.grad is not None
        assert small_model.user_bias.weight.grad is not None
        assert small_model.item_bias.weight.grad is not None

    def test_global_bias_gradient_is_nonzero(
        self,
        small_model: BiasedMatrixFactorization,
        batch_inputs: tuple[torch.Tensor, torch.Tensor],
    ) -> None:
        """Global bias receives non-zero gradients."""
        user_ids, item_ids = batch_inputs
        targets = torch.rand(32) * 4 + 1

        predictions = small_model(user_ids, item_ids)
        loss = nn.MSELoss()(predictions, targets)
        loss.backward()

        assert small_model.global_bias.grad.item() != 0.0

    def test_only_used_embeddings_receive_gradients(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """Only embeddings for used user/item IDs receive gradients."""
        # Use only user 0 and item 0
        user_ids = torch.tensor([0, 0])
        item_ids = torch.tensor([0, 0])
        targets = torch.tensor([4.0, 5.0])

        predictions = small_model(user_ids, item_ids)
        loss = nn.MSELoss()(predictions, targets)
        loss.backward()

        # User 0 embedding should have gradients
        assert small_model.user_embedding.weight.grad[0].abs().sum() > 0

        # User 1 embedding should have zero gradients (not used)
        assert torch.allclose(
            small_model.user_embedding.weight.grad[1],
            torch.zeros_like(small_model.user_embedding.weight.grad[1])
        )


# -----------------------------------------------------------------------------
# Model Configuration Tests
# -----------------------------------------------------------------------------


class TestModelConfiguration:
    """Tests for get_config() and get_num_parameters() methods."""

    def test_get_config_returns_correct_values(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """get_config() returns correct model configuration."""
        config = small_model.get_config()
        assert config['n_users'] == 100
        assert config['n_items'] == 50
        assert config['n_factors'] == 10
        assert config['global_bias'] == pytest.approx(4.0)
        assert 'n_parameters' in config

    def test_get_num_parameters_counts_correctly(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """get_num_parameters() counts all trainable parameters."""
        # Expected parameters:
        # - global_bias: 1
        # - user_embedding: 100 * 10 = 1000
        # - item_embedding: 50 * 10 = 500
        # - user_bias: 100 * 1 = 100
        # - item_bias: 50 * 1 = 50
        # Total: 1 + 1000 + 500 + 100 + 50 = 1651
        assert small_model.get_num_parameters() == 1651

    def test_get_num_parameters_large_model(
        self, large_model: BiasedMatrixFactorization
    ) -> None:
        """get_num_parameters() works for large models."""
        # Expected parameters:
        # - global_bias: 1
        # - user_embedding: 5949 * 50 = 297450
        # - item_embedding: 2856 * 50 = 142800
        # - user_bias: 5949 * 1 = 5949
        # - item_bias: 2856 * 1 = 2856
        # Total: 1 + 297450 + 142800 + 5949 + 2856 = 449056
        assert large_model.get_num_parameters() == 449056


# -----------------------------------------------------------------------------
# Model Integration Tests
# -----------------------------------------------------------------------------


class TestModelIntegration:
    """Integration tests for complete training workflows."""

    def test_simple_training_step(
        self, small_model: BiasedMatrixFactorization
    ) -> None:
        """Model can perform a complete training step."""
        optimizer = torch.optim.SGD(small_model.parameters(), lr=0.01)

        user_ids = torch.tensor([0, 1, 2, 3])
        item_ids = torch.tensor([5, 10, 15, 20])
        targets = torch.tensor([4.0, 3.5, 5.0, 2.0])

        # Forward pass
        predictions = small_model(user_ids, item_ids)
        loss = nn.MSELoss()(predictions, targets)
        initial_loss = loss.item()

        # Backward pass + optimization
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Second forward pass
        predictions_after = small_model(user_ids, item_ids)
        loss_after = nn.MSELoss()(predictions_after, targets)

        # Loss should decrease
        assert loss_after.item() < initial_loss

    def test_model_eval_mode_does_not_affect_predictions(
        self,
        small_model: BiasedMatrixFactorization,
        batch_inputs: tuple[torch.Tensor, torch.Tensor],
    ) -> None:
        """Model predictions are same in train vs eval mode."""
        user_ids, item_ids = batch_inputs

        small_model.train()
        train_predictions = small_model(user_ids, item_ids)

        small_model.eval()
        eval_predictions = small_model(user_ids, item_ids)

        # Predictions should be identical (no dropout/batchnorm)
        assert torch.allclose(train_predictions, eval_predictions)

    def test_model_can_overfit_small_dataset(self) -> None:
        """Model can overfit a tiny dataset (sanity check)."""
        model = BiasedMatrixFactorization(
            n_users=5,
            n_items=3,
            n_factors=10,
            global_mean=3.0,
        )
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1, weight_decay=0.0)

        # Tiny dataset: 4 ratings
        user_ids = torch.tensor([0, 1, 2, 3])
        item_ids = torch.tensor([0, 1, 2, 0])
        targets = torch.tensor([5.0, 3.0, 4.0, 2.0])

        # Train for many epochs
        for _ in range(100):
            optimizer.zero_grad()
            predictions = model(user_ids, item_ids)
            loss = nn.MSELoss()(predictions, targets)
            loss.backward()
            optimizer.step()

        # Final predictions should be very close to targets
        final_predictions = model(user_ids, item_ids)
        final_loss = nn.MSELoss()(final_predictions, targets).item()
        assert final_loss < 0.01  # Should nearly memorize


# -----------------------------------------------------------------------------
# Edge Cases and Validation
# -----------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimum_model_size(self) -> None:
        """Model works with minimum viable dimensions."""
        model = BiasedMatrixFactorization(
            n_users=1,
            n_items=1,
            n_factors=1,
        )
        user_ids = torch.tensor([0])
        item_ids = torch.tensor([0])
        predictions = model(user_ids, item_ids)
        assert predictions.shape == (1,)

    def test_zero_global_mean(self) -> None:
        """Model handles zero global mean correctly."""
        model = BiasedMatrixFactorization(
            n_users=10,
            n_items=5,
            n_factors=3,
            global_mean=0.0,
        )
        assert model.global_bias.item() == 0.0

    def test_negative_global_mean(self) -> None:
        """Model handles negative global mean (edge case)."""
        model = BiasedMatrixFactorization(
            n_users=10,
            n_items=5,
            n_factors=3,
            global_mean=-1.5,
        )
        assert model.global_bias.item() == pytest.approx(-1.5)

    def test_large_n_factors(self) -> None:
        """Model works with large embedding dimensions."""
        model = BiasedMatrixFactorization(
            n_users=100,
            n_items=50,
            n_factors=200,
        )
        user_ids = torch.tensor([0])
        item_ids = torch.tensor([0])
        predictions = model(user_ids, item_ids)
        assert predictions.shape == (1,)
        assert model.user_embedding.embedding_dim == 200
