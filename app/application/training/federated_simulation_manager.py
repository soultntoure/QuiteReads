"""Federated learning simulation orchestration manager.

Coordinates the end-to-end federated learning experiment lifecycle:
1. Data partitioning across clients
2. Flower simulation execution
3. Metrics collection and persistence
4. Experiment state management

This is the main entry point for running federated experiments from the
application layer, bridging domain entities and FL infrastructure.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.application.data.partitioner import PartitionConfig, UserPartitioner
from app.utils.exceptions import FederatedSimulationError


@dataclass
class FederatedSimulationResult:
    """Result of a federated simulation run.
    
    Captures all metrics from Flower simulation in a format suitable
    for persistence via ExperimentManager.
    
    Attributes:
        final_rmse: Final centralized test RMSE (from last round).
        final_mae: Final centralized test MAE (from last round).
        best_rmse: Best centralized test RMSE achieved.
        best_mae: MAE at the round with best RMSE.
        best_round: Round number that achieved best RMSE.
        training_time_seconds: Total simulation wall-clock time.
        num_rounds: Total number of federated rounds completed.
        metrics_by_round: Per-round metrics for database persistence.
        raw_result: Original Flower FedAvgResult object for debugging.
    """
    
    final_rmse: float
    final_mae: float
    best_rmse: float
    best_mae: float
    best_round: int
    training_time_seconds: float
    num_rounds: int
    metrics_by_round: List[Dict[str, Any]] = field(default_factory=list)
    raw_result: Optional[Any] = None  # FedAvgResult from strategy.start()
    
    @property
    def converged_rmse(self) -> float:
        """Return the final RMSE for convergence analysis."""
        return self.final_rmse
    
    @property
    def improvement_over_rounds(self) -> float:
        """Calculate RMSE improvement from first to last round."""
        if not self.metrics_by_round:
            return 0.0
        first_rmse = self.metrics_by_round[0].get("test_rmse", self.final_rmse)
        return first_rmse - self.final_rmse


class FederatedSimulationManager:
    """Orchestrates federated simulation and bridges to domain services.
    
    This manager mirrors the structure of CentralizedTrainer but for
    federated learning. It handles:
    - Data partitioning via UserPartitioner
    - Flower simulation execution via run_simulation()
    - Metrics extraction from Flower History
    - Result packaging for database persistence
    
    Example:
        >>> manager = FederatedSimulationManager(
        ...     data_dir=Path("data"),
        ...     storage_dir=Path("results/federated"),
        ...     num_clients=10,
        ... )
        >>> result = manager.run_simulation(
        ...     num_rounds=10,
        ...     n_factors=16,
        ... )
        >>> print(f"Final RMSE: {result.final_rmse:.4f}")
    """
    
    def __init__(
        self,
        data_dir: Path,
        storage_dir: Path,
        num_clients: int = 10,
        random_seed: int = 42,
    ):
        """Initialize the federated simulation manager.
        
        Args:
            data_dir: Path to the preprocessed data directory containing
                train.parquet, val.parquet, test.parquet, and metadata.json.
            storage_dir: Directory for partitions and simulation artifacts.
            num_clients: Number of federated clients to simulate.
            random_seed: Seed for reproducible partitioning.
        """
        self.data_dir = Path(data_dir)
        self.storage_dir = Path(storage_dir)
        self.num_clients = num_clients
        self.random_seed = random_seed
        
        # Lazily initialized
        self._partition_result: Optional[Any] = None
    
    def _partition_data(self, force: bool = False) -> Path:
        """Partition dataset for federated clients.
        
        Uses UserPartitioner to create per-client train/val splits.
        Partitions are cached - subsequent calls return existing partition
        unless force=True.
        
        Args:
            force: If True, re-partition even if partitions exist.
            
        Returns:
            Path to the partition directory containing client data.
        """
        partition_dir = self.storage_dir / "partitions"
        config_path = partition_dir / "partition_config.json"
        
        # Check if partitions already exist
        if not force and config_path.exists():
            self._partition_result = partition_dir
            return partition_dir
        
        # Create partitioner and partition data
        config = PartitionConfig(
            num_clients=self.num_clients,
            seed=self.random_seed,
        )
        partitioner = UserPartitioner(config=config)
        
        # Run partitioning
        result = partitioner.partition(
            data_dir=self.data_dir,
            output_dir=partition_dir,
        )
        
        self._partition_result = result
        return partition_dir
    
    def _build_run_config(
        self,
        partition_dir: Path,
        num_rounds: int,
        n_factors: int,
        learning_rate: float = 0.02,
        regularization: float = 0.005,
        local_epochs: int = 5,
        batch_size: int = 1024,
        fraction_train: float = 1.0,
        fraction_evaluate: float = 1.0,
        enable_centralized_eval: bool = True,
        user_lr: float = 0.1,
        user_epochs: int = 3,
    ) -> Dict[str, Any]:
        """Build Flower run_config dictionary.
        
        Constructs the configuration dictionary passed to Flower's
        run_simulation via context.run_config.
        
        Args:
            partition_dir: Path to partitioned data.
            num_rounds: Number of federated rounds.
            n_factors: Latent factor dimension.
            learning_rate: Client-side learning rate.
            regularization: L2 regularization weight.
            local_epochs: Epochs per client per round.
            batch_size: Batch size for client DataLoaders.
            fraction_train: Fraction of clients selected for training.
            fraction_evaluate: Fraction of clients for evaluation.
            enable_centralized_eval: Whether to run server-side test eval.
            user_lr: Learning rate for user embedding fine-tuning.
            user_epochs: Epochs for user embedding training in centralized eval.
            
        Returns:
            Dictionary of run configuration options.
        """
        return {
            # Data paths
            "data-dir": str(self.data_dir),
            "partition-dir": str(partition_dir),
            "output-dir": str(self.storage_dir),
            
            # Training configuration
            "num-rounds": num_rounds,
            "n-factors": n_factors,
            "learning-rate": learning_rate,
            "regularization": regularization,
            "local-epochs": local_epochs,
            "batch-size": batch_size,
            
            # Client selection
            "fraction-train": fraction_train,
            "fraction-evaluate": fraction_evaluate,
            "min-train-clients": min(2, self.num_clients),
            "min-evaluate-clients": min(2, self.num_clients),
            "min-available-clients": min(2, self.num_clients),
            
            # Centralized evaluation
            "centralized-eval": enable_centralized_eval,
            "user-lr": user_lr,
            "user-epochs": user_epochs,
        }
    
    def _run_flower_simulation(
        self,
        run_config: Dict[str, Any],
    ) -> Any:
        """Run Flower simulation programmatically.
        
        Invokes Flower's run_simulation() with server and client apps
        from the federated module.
        
        Args:
            run_config: Configuration dictionary for the simulation.
            
        Returns:
            History object from run_simulation() containing metrics_centralized,
            metrics_distributed, and losses_distributed as lists of (round, value) tuples.
        """
        from flwr.simulation import run_simulation
        
        from app.application.federated.client_app import app as client_app
        from app.application.federated.server_app import app as server_app
        
        # Run simulation and return History object
        history = run_simulation(
            server_app=server_app,
            client_app=client_app,
            num_supernodes=self.num_clients,
            backend_config={
                "client_resources": {
                    "num_cpus": 1,
                    "num_gpus": 0.0,
                },
            },
            run_config=run_config,
        )
        
        return history
    
    def _extract_metrics_from_result(
        self,
        result: Any,
        num_rounds: int,
    ) -> List[Dict[str, Any]]:
        """Extract per-round metrics from Flower History object.
        
        Converts Flower's History object (returned by run_simulation) into a list
        of per-round metric dictionaries suitable for database persistence.
        
        Note: run_simulation() returns a History object, NOT the FedAvgResult
        from strategy.start(). The FedAvgResult with richer metrics is internal
        to server_app.main() and doesn't propagate out. For access to those
        metrics, read the final_metrics.json file saved by server_app.py.
        
        Args:
            result: History object from run_simulation().
            num_rounds: Number of rounds completed.
            
        Returns:
            List of dictionaries with per-round metrics:
                - round: Round number (1-indexed)
                - test_rmse: Centralized test RMSE (if available)
                - test_mae: Centralized test MAE (if available)
                - client_eval_rmse: Aggregated client validation RMSE (if available)
                - client_eval_mae: Aggregated client validation MAE (if available)
                - train_loss: Aggregated training loss (if available)
        """
        metrics_by_round = []
        
        # History object from run_simulation
        # Optimize with dict pre-pass to avoid O(rounds²) nested loops
        
        # Pre-pass: Convert list of (round, value) tuples to dicts (O(rounds) per metric)
        centralized_metrics = {}
        if hasattr(result, 'metrics_centralized') and result.metrics_centralized:
            for metric_name, tuples in result.metrics_centralized.items():
                centralized_metrics[metric_name] = dict(tuples)
        
        distributed_metrics = {}
        if hasattr(result, 'metrics_distributed') and result.metrics_distributed:
            for metric_name, tuples in result.metrics_distributed.items():
                distributed_metrics[metric_name] = dict(tuples)
        
        distributed_losses = {}
        if hasattr(result, 'losses_distributed') and result.losses_distributed:
            distributed_losses = dict(result.losses_distributed)
        
        # Single-pass: Build per-round metrics with O(1) dict lookups
        for round_num in range(1, num_rounds + 1):
            round_metrics = {"round": round_num}
            
            # Centralized evaluation metrics (server-side test set)
            if "test_rmse" in centralized_metrics:
                round_metrics["test_rmse"] = centralized_metrics["test_rmse"].get(round_num)
            if "test_mae" in centralized_metrics:
                round_metrics["test_mae"] = centralized_metrics["test_mae"].get(round_num)
            if "test_loss" in centralized_metrics:
                round_metrics["test_loss"] = centralized_metrics["test_loss"].get(round_num)
            
            # Client-side evaluation metrics (distributed validation)
            if "eval_rmse" in distributed_metrics:
                round_metrics["client_eval_rmse"] = distributed_metrics["eval_rmse"].get(round_num)
            if "eval_mae" in distributed_metrics:
                round_metrics["client_eval_mae"] = distributed_metrics["eval_mae"].get(round_num)
            
            # Training loss
            if distributed_losses:
                round_metrics["train_loss"] = distributed_losses.get(round_num)
            
            metrics_by_round.append(round_metrics)
        
        return metrics_by_round
    
    def run_simulation(
        self,
        num_rounds: int = 10,
        n_factors: int = 16,
        learning_rate: float = 0.02,
        regularization: float = 0.005,
        local_epochs: int = 5,
        batch_size: int = 1024,
        fraction_train: float = 1.0,
        fraction_evaluate: float = 1.0,
        enable_centralized_eval: bool = True,
        user_lr: float = 0.1,
        user_epochs: int = 3,
        force_repartition: bool = False,
    ) -> FederatedSimulationResult:
        """Run complete federated simulation.
        
        Main entry point that mirrors run_centralized_experiment() structure.
        Handles data partitioning, Flower simulation, and metrics extraction.
        
        Args:
            num_rounds: Number of federated communication rounds.
            n_factors: Latent factor dimension for matrix factorization.
            learning_rate: Client-side optimizer learning rate.
            regularization: L2 regularization weight.
            local_epochs: Training epochs per client per round.
            batch_size: Batch size for client DataLoaders.
            fraction_train: Fraction of clients selected for training.
            fraction_evaluate: Fraction of clients for evaluation.
            enable_centralized_eval: Enable server-side test set evaluation.
            user_lr: Learning rate for user embedding in centralized eval.
            user_epochs: Epochs for user embedding training.
            force_repartition: Force re-partitioning even if cached.
            
        Returns:
            FederatedSimulationResult with all metrics for persistence.
            
        Raises:
            RuntimeError: If simulation fails.
            FileNotFoundError: If data files are missing.
        """
        start_time = time.time()
        
        # 1. Partition data (uses cache if available)
        partition_dir = self._partition_data(force=force_repartition)
        
        # 2. Build Flower run_config
        run_config = self._build_run_config(
            partition_dir=partition_dir,
            num_rounds=num_rounds,
            n_factors=n_factors,
            learning_rate=learning_rate,
            regularization=regularization,
            local_epochs=local_epochs,
            batch_size=batch_size,
            fraction_train=fraction_train,
            fraction_evaluate=fraction_evaluate,
            enable_centralized_eval=enable_centralized_eval,
            user_lr=user_lr,
            user_epochs=user_epochs,
        )
        
        # 3. Run Flower simulation
        result = self._run_flower_simulation(run_config)
        
        training_time = time.time() - start_time
        
        # 4. Extract metrics from result
        metrics_by_round = self._extract_metrics_from_result(result, num_rounds)
        
        # 5. Calculate final and best metrics
        final_rmse = float("inf")
        final_mae = float("inf")
        best_rmse = float("inf")
        best_mae = float("inf")
        best_round = 0
        
        for round_data in metrics_by_round:
            round_num = round_data.get("round", 0)
            test_rmse = round_data.get("test_rmse")
            test_mae = round_data.get("test_mae")
            
            if test_rmse is not None:
                final_rmse = test_rmse
                final_mae = test_mae if test_mae is not None else final_mae
                
                if test_rmse < best_rmse:
                    best_rmse = test_rmse
                    best_mae = test_mae if test_mae is not None else 0.0
                    best_round = round_num
        
        # Handle case where no centralized eval was run
        if final_rmse == float("inf"):
            # Fall back to client-side metrics
            for round_data in metrics_by_round:
                client_rmse = round_data.get("client_eval_rmse")
                client_mae = round_data.get("client_eval_mae")
                
                if client_rmse is not None:
                    final_rmse = client_rmse
                    final_mae = client_mae if client_mae is not None else 0.0
                    
                    if client_rmse < best_rmse:
                        best_rmse = client_rmse
                        best_mae = client_mae if client_mae is not None else 0.0
                        best_round = round_data.get("round", 0)
        
        # 6. Validate that metrics were produced
        if final_rmse == float("inf"):
            raise FederatedSimulationError(
                "No evaluation metrics were produced during federated simulation. "
                "Either enable centralized evaluation (enable_centralized_eval=True) "
                "or ensure clients have validation data for distributed evaluation."
            )
        
        # 7. Return result
        return FederatedSimulationResult(
            final_rmse=final_rmse,
            final_mae=final_mae,
            best_rmse=best_rmse,
            best_mae=best_mae,
            best_round=best_round,
            training_time_seconds=training_time,
            num_rounds=num_rounds,
            metrics_by_round=metrics_by_round,
            raw_result=result,
        )