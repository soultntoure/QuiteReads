"""
Flower ServerApp for Federated Matrix Factorization.

Orchestrates federated rounds using FedAvgItemsOnly strategy and centralized evaluation.

Key Features:
- Global model initialization: Full dimensions
- FedAvgItemsOnly strategy: Aggregates only item-side parameters
- Centralized evaluation: Tests global model on full test.parquet split
- Metric aggregation: Weighted average of local val_rmse and val_mae

Usage:
    # Run with Flower simulation
    flwr run . --run-config partition-dir=data/federated

    # Or programmatically
    from app.application.federated.server_app import app
"""
