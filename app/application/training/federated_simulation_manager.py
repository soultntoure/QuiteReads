"""Federated learning simulation orchestration manager.

Coordinates the end-to-end federated learning experiment lifecycle:
1. Data partitioning across clients
2. Flower simulation execution
3. Metrics collection and persistence
4. Experiment state management

This is the main entry point for running federated experiments from the
application layer, bridging domain entities and FL infrastructure.
"""