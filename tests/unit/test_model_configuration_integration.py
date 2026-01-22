"""Integration tests for model + configuration.

Tests verify that the BiasedMatrixFactorization model integrates
correctly with the domain Configuration entity.
"""

import pytest
import torch

from app.core.configuration import Configuration
from app.core.models.matrix_factorization import BiasedMatrixFactorization
from app.utils.types import ModelType


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def default_config() -> Configuration:
    """Create default configuration."""
    return Configuration(
        model_type=ModelType.BIASED_SVD,
        n_factors=20,
        learning_rate=0.005,
        regularization=0.02,
        n_epochs=10,
    )


@pytest.fixture
def custom_config() -> Configuration:
    """Create custom configuration."""
    return Configuration(
        model_type=ModelType.BIASED_SVD,
        n_factors=50,
        learning_rate=0.01,
        regularization=0.05,
        n_epochs=5,
    )


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


class TestModelConfigurationIntegration:
    """Tests for BiasedMatrixFactorization + Configuration integration."""

    def test_model_created_from_config_parameters(
        self, default_config: Configuration
    ) -> None:
        """Model can be created using Configuration parameters."""
        # Simulate dataset metadata
        n_users = 1000
        n_items = 500
        global_mean = 3.75

        # Create model using config.n_factors
        model = BiasedMatrixFactorization(
            n_users=n_users,
            n_items=n_items,
            n_factors=default_config.n_factors,
            global_mean=global_mean,
        )

        assert model.n_factors == default_config.n_factors
        assert model.n_users == n_users
        assert model.n_items == n_items
        assert model.global_bias.item() == pytest.approx(global_mean)

    def test_model_respects_different_n_factors(
        self, custom_config: Configuration
    ) -> None:
        """Model embedding dimensions match config.n_factors."""
        model = BiasedMatrixFactorization(
            n_users=100,
            n_items=50,
            n_factors=custom_config.n_factors,
            global_mean=4.0,
        )

        assert model.n_factors == 50
        assert model.user_embedding.embedding_dim == 50
        assert model.item_embedding.embedding_dim == 50

    def test_optimizer_created_from_config_parameters(
        self, default_config: Configuration
    ) -> None:
        """Optimizer can be created using Configuration parameters."""
        model = BiasedMatrixFactorization(
            n_users=100,
            n_items=50,
            n_factors=default_config.n_factors,
            global_mean=4.0,
        )

        # Create optimizer using config.learning_rate and config.regularization
        optimizer = torch.optim.SGD(
            model.parameters(),
            lr=default_config.learning_rate,
            weight_decay=default_config.regularization,
        )

        # Verify optimizer uses correct learning rate
        assert optimizer.param_groups[0]['lr'] == default_config.learning_rate
        assert optimizer.param_groups[0]['weight_decay'] == default_config.regularization

    def test_training_loop_uses_config_epochs(
        self, default_config: Configuration
    ) -> None:
        """Training can use config.n_epochs for loop control."""
        model = BiasedMatrixFactorization(
            n_users=10,
            n_items=5,
            n_factors=default_config.n_factors,
            global_mean=3.0,
        )
        optimizer = torch.optim.SGD(model.parameters(), lr=default_config.learning_rate)

        # Simulate training loop using config.n_epochs
        epochs_completed = 0
        for epoch in range(default_config.n_epochs):
            # Dummy training step
            user_ids = torch.tensor([0, 1])
            item_ids = torch.tensor([0, 1])
            targets = torch.tensor([4.0, 5.0])

            predictions = model(user_ids, item_ids)
            loss = torch.nn.MSELoss()(predictions, targets)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epochs_completed += 1

        assert epochs_completed == default_config.n_epochs

    def test_model_type_enum_matches_implementation(
        self, default_config: Configuration
    ) -> None:
        """Configuration.model_type enum aligns with model implementation."""
        assert default_config.model_type == ModelType.BIASED_SVD

        # When model_type is BIASED_SVD, we use BiasedMatrixFactorization
        # This test documents the intended mapping
        if default_config.model_type == ModelType.BIASED_SVD:
            model = BiasedMatrixFactorization(
                n_users=100,
                n_items=50,
                n_factors=default_config.n_factors,
            )
            assert model is not None


# -----------------------------------------------------------------------------
# Configuration Validation Tests
# -----------------------------------------------------------------------------


class TestConfigurationValidation:
    """Tests for Configuration validation rules."""

    def test_invalid_n_factors_raises_error(self) -> None:
        """n_factors outside valid range raises ValueError."""
        with pytest.raises(ValueError, match="n_factors must be 1-200"):
            Configuration(n_factors=0)

        with pytest.raises(ValueError, match="n_factors must be 1-200"):
            Configuration(n_factors=201)

    def test_invalid_learning_rate_raises_error(self) -> None:
        """learning_rate outside valid range raises ValueError."""
        with pytest.raises(ValueError, match="learning_rate must be"):
            Configuration(learning_rate=0.0)

        with pytest.raises(ValueError, match="learning_rate must be"):
            Configuration(learning_rate=1.5)

    def test_valid_boundary_values(self) -> None:
        """Boundary values for n_factors and learning_rate are valid."""
        config = Configuration(n_factors=1, learning_rate=0.001)
        assert config.n_factors == 1
        assert config.learning_rate == 0.001

        config = Configuration(n_factors=200, learning_rate=1.0)
        assert config.n_factors == 200
        assert config.learning_rate == 1.0
