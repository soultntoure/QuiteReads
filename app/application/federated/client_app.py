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

