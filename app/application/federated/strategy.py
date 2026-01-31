"""
Custom Federated Aggregation Strategy.

Implements FedAvgItemsOnly: aggregates only item-side parameters
(item embeddings, item biases, global bias) while keeping user embeddings local.

This implementation uses Flower's Message API with name-based parameter filtering.
"""
