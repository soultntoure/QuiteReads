# Project Structure

```text
src/
├── __init__.py - Main package initialization for FedRec Experiments
│
├── data/
│   ├── __init__.py - Data package initialization
│   ├── .gitkeep - Placeholder file to keep empty directory in git
│   ├── README.md - Documentation for data module
│   ├── datamodule.py - PyTorch Lightning DataModule for centralized training with RatingsDataset and train/val/test DataLoaders
│   ├── preprocessing.py - Data preprocessing pipeline that filters Goodreads interactions, creates ID mappings, and generates train/val/test splits
│   └── federated_datamodule.py - Client-specific DataModule for federated learning that loads partitioned user data per client
│
├── models/
│   ├── __init__.py - Models package initialization
│   ├── .gitkeep - Placeholder file to keep empty directory in git
│   ├── README.md - Documentation for models module
│   ├── matrix_factorization.py - BiasedMatrixFactorization model implementing r̂ = μ + b_u + b_i + p_u·q_i for rating prediction
│   └── lightning_module.py - LitBiasedMatrixFactorization wrapper for PyTorch Lightning training with RMSE/MAE metrics and optimizer configuration
│
├── utils/
│   ├── __init__.py - Utils package initialization exporting set_seeds and get_device
│   ├── .gitkeep - Placeholder file to keep empty directory in git
│   ├── README.md - Documentation for utils module
│   └── reproducibility.py - Utility functions for setting random seeds across libraries and detecting available compute devices
│
├── federated/
│   ├── __init__.py - Federated learning package initialization
│   ├── .gitkeep - Placeholder file to keep empty directory in git
│   ├── README.md - Documentation for federated module
│   ├── partitioner.py - UserPartitioner for IID user-based data partitioning across federated clients with exclusive user assignments
│   ├── client_app.py - Flower ClientApp implementing @train() and @evaluate() with user embedding persistence and item-only communication
│   ├── server_app.py - Flower ServerApp orchestrating federated rounds with FedAvgItemsOnly strategy and centralized evaluation on test set
│   └── strategy.py - FedAvgItemsOnly strategy that aggregates only item-side parameters (global_bias, item_embedding, item_bias) while keeping user embeddings local
│
└── callbacks/
    ├── __init__.py - Callbacks package initialization
    └── epoch_metrics_callback.py - EpochMetricsCallback for capturing per-epoch training and validation metrics for convergence analysis plots
```

## Summary by Module

- **data/**: Data loading and preprocessing infrastructure for both centralized and federated scenarios
- **models/**: Neural network architectures and PyTorch Lightning training modules for matrix factorization
- **utils/**: Helper utilities for reproducibility and device management
- **federated/**: Complete federated learning implementation using Flower framework with custom aggregation strategy
- **callbacks/**: Custom PyTorch Lightning callbacks for metric tracking during training
