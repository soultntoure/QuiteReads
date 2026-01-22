"""
Biased Matrix Factorization Model
=================================

PyTorch implementation of Matrix Factorization with user/item biases
for rating prediction in recommender systems.

Model: r̂_ui = μ + b_u + b_i + p_u^T · q_i

Where:
    μ   = global mean rating
    b_u = user bias (how much user u deviates from mean)
    b_i = item bias (how much item i deviates from mean)
    p_u = user latent factors (embedding)
    q_i = item latent factors (embedding)

Usage:
    from app.core.models.matrix_factorization import BiasedMatrixFactorization

    model = BiasedMatrixFactorization(
        n_users=5949,
        n_items=2856,
        n_factors=50,
        global_mean=4.07
    )

    predictions = model(user_ids, item_ids)
"""

import torch
import torch.nn as nn


class BiasedMatrixFactorization(nn.Module):
    """Biased Matrix Factorization for rating prediction.

    This model learns:
    - User embeddings: latent factors representing user preferences
    - Item embeddings: latent factors representing item characteristics
    - User biases: per-user rating tendencies
    - Item biases: per-item rating tendencies
    - Global bias: trainable global mean rating

    The prediction is: r̂ = μ + b_u + b_i + p_u · q_i

    Args:
        n_users: Number of unique users
        n_items: Number of unique items
        n_factors: Dimension of latent factors (default: 50)
        global_mean: Initial mean rating from training data (default: 0.0)

    Example:
        >>> model = BiasedMatrixFactorization(1000, 500, n_factors=50, global_mean=3.5)
        >>> users = torch.tensor([0, 1, 2])
        >>> items = torch.tensor([10, 20, 30])
        >>> predictions = model(users, items)
        >>> predictions.shape
        torch.Size([3])
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        n_factors: int = 16,
        global_mean: float = 0.0
    ):
        super().__init__()

        self.n_users = n_users
        self.n_items = n_items
        self.n_factors = n_factors

        # Global bias (μ) - trainable parameter initialized with global_mean
        self.global_bias = nn.Parameter(torch.tensor(float(global_mean)))

        # User and item embeddings (latent factors)
        self.user_embedding = nn.Embedding(n_users, n_factors)
        self.item_embedding = nn.Embedding(n_items, n_factors)

        # User and item biases
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_items, 1)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize embeddings and biases.

        - Embeddings: Normal distribution with small std (0.01)
        - Biases: Zeros (let them learn from data)
        """
        nn.init.normal_(self.user_embedding.weight, mean=0.0, std=0.01)
        nn.init.normal_(self.item_embedding.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.item_bias.weight)

    def forward(
        self,
        user_ids: torch.Tensor,
        item_ids: torch.Tensor
    ) -> torch.Tensor:
        """Compute rating predictions.

        Args:
            user_ids: Tensor of user indices, shape (batch_size,)
            item_ids: Tensor of item indices, shape (batch_size,)

        Returns:
            Predicted ratings, shape (batch_size,)
        """
        # Look up embeddings: (batch_size, n_factors)
        user_emb = self.user_embedding(user_ids)
        item_emb = self.item_embedding(item_ids)

        # Look up biases: (batch_size, 1) -> (batch_size,)
        user_b = self.user_bias(user_ids).squeeze(-1)
        item_b = self.item_bias(item_ids).squeeze(-1)

        # Dot product of latent factors: (batch_size,)
        dot_product = (user_emb * item_emb).sum(dim=1)

        # Final prediction: μ + b_u + b_i + p_u · q_i
        prediction = self.global_bias + user_b + item_b + dot_product

        return prediction

    def get_num_parameters(self) -> int:
        """Return total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_config(self) -> dict:
        """Return model configuration for logging."""
        return {
            'n_users': self.n_users,
            'n_items': self.n_items,
            'n_factors': self.n_factors,
            'global_bias': self.global_bias.item(),
            'n_parameters': self.get_num_parameters()
        }
