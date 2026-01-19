"""Integration tests for API routes.

Tests complete API layer with database persistence.
Uses TestClient and SQLite in-memory database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.main import app
from app.infrastructure import get_session
from app.infrastructure.database import Base


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def async_engine():
    """Create async SQLite in-memory engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(async_engine) -> AsyncSession:
    """Create async session for testing with proper transaction handling."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(test_session: AsyncSession):
    """Create TestClient with dependency override for test database."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# Test Health Endpoint
# -----------------------------------------------------------------------------


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Health check should return 200 with status healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# -----------------------------------------------------------------------------
# Test Create Experiment Endpoints
# -----------------------------------------------------------------------------


class TestCreateCentralizedExperiment:
    """Tests for POST /experiments/centralized."""

    def test_create_centralized_success(self, client: TestClient):
        """Successfully create centralized experiment."""
        payload = {
            "name": "Test Centralized Baseline",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        }

        response = client.post("/experiments/centralized", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Centralized Baseline"
        assert data["type"] == "centralized"
        assert data["status"] == "pending"
        assert "id" in data
        assert data["config"]["learning_rate"] == 0.01
        assert data["config"]["epochs"] == 10

    def test_create_centralized_invalid_learning_rate(self, client: TestClient):
        """Creating with invalid learning rate returns 422."""
        payload = {
            "name": "Invalid LR",
            "config": {
                "learning_rate": 1.5,  # Invalid: > 1.0
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        }

        response = client.post("/experiments/centralized", json=payload)
        assert response.status_code == 422

    def test_create_centralized_empty_name(self, client: TestClient):
        """Creating with empty name returns 422."""
        payload = {
            "name": "",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        }

        response = client.post("/experiments/centralized", json=payload)
        assert response.status_code == 422


class TestCreateFederatedExperiment:
    """Tests for POST /experiments/federated."""

    def test_create_federated_success(self, client: TestClient):
        """Successfully create federated experiment."""
        payload = {
            "name": "Test Federated FL",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "biased_svd"
            },
            "n_clients": 5,
            "n_rounds": 20,
            "aggregation_strategy": "fedavg"
        }

        response = client.post("/experiments/federated", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Federated FL"
        assert data["type"] == "federated"
        assert data["status"] == "pending"
        assert data["n_clients"] == 5
        assert data["n_rounds"] == 20
        assert data["aggregation_strategy"] == "fedavg"

    def test_create_federated_invalid_n_clients(self, client: TestClient):
        """Creating with invalid n_clients returns 422."""
        payload = {
            "name": "Invalid Clients",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "biased_svd"
            },
            "n_clients": 1,  # Invalid: < 2
            "n_rounds": 20,
            "aggregation_strategy": "fedavg"
        }

        response = client.post("/experiments/federated", json=payload)
        assert response.status_code == 422

    def test_create_federated_invalid_n_rounds(self, client: TestClient):
        """Creating with invalid n_rounds returns 422."""
        payload = {
            "name": "Invalid Rounds",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "biased_svd"
            },
            "n_clients": 5,
            "n_rounds": 0,  # Invalid: < 1
            "aggregation_strategy": "fedavg"
        }

        response = client.post("/experiments/federated", json=payload)
        assert response.status_code == 422


# -----------------------------------------------------------------------------
# Test Get Experiment Endpoints
# -----------------------------------------------------------------------------


class TestGetExperiment:
    """Tests for GET /experiments/{experiment_id}."""

    def test_get_existing_experiment(self, client: TestClient):
        """Successfully retrieve existing experiment."""
        # Create experiment first
        create_payload = {
            "name": "Test Get",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        }
        create_response = client.post("/experiments/centralized", json=create_payload)
        experiment_id = create_response.json()["id"]

        # Retrieve it
        response = client.get(f"/experiments/{experiment_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == experiment_id
        assert data["name"] == "Test Get"

    def test_get_nonexistent_experiment(self, client: TestClient):
        """Getting nonexistent experiment returns 404."""
        response = client.get("/experiments/nonexistent-id-12345")
        assert response.status_code == 404


class TestListExperiments:
    """Tests for GET /experiments."""

    def test_list_empty(self, client: TestClient):
        """List experiments when none exist returns empty list."""
        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert data["experiments"] == []
        assert data["count"] == 0

    def test_list_multiple_experiments(self, client: TestClient):
        """List returns all experiments."""
        # Create centralized experiment
        client.post("/experiments/centralized", json={
            "name": "Centralized 1",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })

        # Create federated experiment
        client.post("/experiments/federated", json={
            "name": "Federated 1",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "biased_svd"
            },
            "n_clients": 5,
            "n_rounds": 20,
            "aggregation_strategy": "fedavg"
        })

        # List all
        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["experiments"]) == 2

    def test_filter_by_status(self, client: TestClient):
        """Filter experiments by status."""
        # Create experiment and start it
        create_response = client.post("/experiments/centralized", json={
            "name": "Running Exp",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        exp_id = create_response.json()["id"]
        client.post(f"/experiments/{exp_id}/start")

        # Create another pending experiment
        client.post("/experiments/centralized", json={
            "name": "Pending Exp",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })

        # Filter by running
        response = client.get("/experiments?status_filter=running")
        data = response.json()
        assert data["count"] == 1
        assert data["experiments"][0]["status"] == "running"

        # Filter by pending
        response = client.get("/experiments?status_filter=pending")
        data = response.json()
        assert data["count"] == 1
        assert data["experiments"][0]["status"] == "pending"

    def test_filter_by_type(self, client: TestClient):
        """Filter experiments by type."""
        # Create centralized
        client.post("/experiments/centralized", json={
            "name": "Centralized",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })

        # Create federated
        client.post("/experiments/federated", json={
            "name": "Federated",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "biased_svd"
            },
            "n_clients": 5,
            "n_rounds": 20,
            "aggregation_strategy": "fedavg"
        })

        # Filter by centralized
        response = client.get("/experiments?type_filter=centralized")
        data = response.json()
        assert data["count"] == 1
        assert data["experiments"][0]["type"] == "centralized"

        # Filter by federated
        response = client.get("/experiments?type_filter=federated")
        data = response.json()
        assert data["count"] == 1
        assert data["experiments"][0]["type"] == "federated"


# -----------------------------------------------------------------------------
# Test Experiment Lifecycle Endpoints
# -----------------------------------------------------------------------------


class TestStartExperiment:
    """Tests for POST /experiments/{experiment_id}/start."""

    def test_start_pending_experiment_success(self, client: TestClient):
        """Successfully start pending experiment."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Start Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Start it
        response = client.post(f"/experiments/{experiment_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_start_nonexistent_experiment(self, client: TestClient):
        """Starting nonexistent experiment returns 404."""
        response = client.post("/experiments/nonexistent-id/start")
        assert response.status_code == 404

    def test_start_already_running_experiment(self, client: TestClient):
        """Starting already running experiment returns 422."""
        # Create and start experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Already Running",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]
        client.post(f"/experiments/{experiment_id}/start")

        # Try to start again
        response = client.post(f"/experiments/{experiment_id}/start")
        assert response.status_code == 422


class TestCompleteExperiment:
    """Tests for POST /experiments/{experiment_id}/complete."""

    def test_complete_running_experiment_success(self, client: TestClient):
        """Successfully complete running experiment with metrics."""
        # Create and start experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Complete Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]
        client.post(f"/experiments/{experiment_id}/start")

        # Complete it with metrics
        complete_payload = {
            "final_rmse": 0.85,
            "final_mae": 0.65,
            "training_time_seconds": 120.5
        }
        response = client.post(f"/experiments/{experiment_id}/complete", json=complete_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["metrics"]["final_rmse"] == 0.85
        assert data["metrics"]["final_mae"] == 0.65
        assert data["metrics"]["training_time_seconds"] == 120.5

    def test_complete_nonexistent_experiment(self, client: TestClient):
        """Completing nonexistent experiment returns 404."""
        complete_payload = {
            "final_rmse": 0.85,
            "final_mae": 0.65,
            "training_time_seconds": 120.5
        }
        response = client.post("/experiments/nonexistent-id/complete", json=complete_payload)
        assert response.status_code == 404

    def test_complete_pending_experiment(self, client: TestClient):
        """Completing pending experiment returns 422."""
        # Create but don't start experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Not Started",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Try to complete
        complete_payload = {
            "final_rmse": 0.85,
            "final_mae": 0.65,
            "training_time_seconds": 120.5
        }
        response = client.post(f"/experiments/{experiment_id}/complete", json=complete_payload)
        assert response.status_code == 422


class TestFailExperiment:
    """Tests for POST /experiments/{experiment_id}/fail."""

    def test_fail_running_experiment_success(self, client: TestClient):
        """Successfully mark running experiment as failed."""
        # Create and start experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Fail Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]
        client.post(f"/experiments/{experiment_id}/start")

        # Fail it
        response = client.post(f"/experiments/{experiment_id}/fail")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    def test_fail_nonexistent_experiment(self, client: TestClient):
        """Failing nonexistent experiment returns 404."""
        response = client.post("/experiments/nonexistent-id/fail")
        assert response.status_code == 404


# -----------------------------------------------------------------------------
# Test Delete Experiment Endpoint
# -----------------------------------------------------------------------------


class TestDeleteExperiment:
    """Tests for DELETE /experiments/{experiment_id}."""

    def test_delete_existing_experiment(self, client: TestClient):
        """Successfully delete existing experiment."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Delete Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/experiments/{experiment_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/experiments/{experiment_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_experiment(self, client: TestClient):
        """Deleting nonexistent experiment returns 404."""
        response = client.delete("/experiments/nonexistent-id")
        assert response.status_code == 404


# -----------------------------------------------------------------------------
# Test Metrics Endpoints
# -----------------------------------------------------------------------------


class TestAddMetric:
    """Tests for POST /experiments/{experiment_id}/metrics."""

    def test_add_metric_success(self, client: TestClient):
        """Successfully add metric to experiment."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Metrics Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Add metric
        metric_payload = {
            "name": "rmse",
            "value": 0.75,
            "round_number": 1
        }
        response = client.post(f"/experiments/{experiment_id}/metrics", json=metric_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "rmse"
        assert data["value"] == 0.75
        assert data["round_number"] == 1

    def test_add_metric_nonexistent_experiment(self, client: TestClient):
        """Adding metric to nonexistent experiment returns 404."""
        metric_payload = {
            "name": "rmse",
            "value": 0.75
        }
        response = client.post("/experiments/nonexistent-id/metrics", json=metric_payload)
        assert response.status_code == 404


class TestAddMetricsBatch:
    """Tests for POST /experiments/{experiment_id}/metrics/batch."""

    def test_add_metrics_batch_success(self, client: TestClient):
        """Successfully add batch of metrics."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Batch Metrics Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Add batch metrics
        batch_payload = {
            "metrics": [
                {"name": "rmse", "value": 0.75, "round_number": 1},
                {"name": "mae", "value": 0.55, "round_number": 1},
                {"name": "rmse", "value": 0.70, "round_number": 2}
            ]
        }
        response = client.post(f"/experiments/{experiment_id}/metrics/batch", json=batch_payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3

    def test_add_metrics_batch_nonexistent_experiment(self, client: TestClient):
        """Adding batch metrics to nonexistent experiment returns 404."""
        batch_payload = {
            "metrics": [
                {"name": "rmse", "value": 0.75}
            ]
        }
        response = client.post("/experiments/nonexistent-id/metrics/batch", json=batch_payload)
        assert response.status_code == 404


class TestGetMetrics:
    """Tests for GET /experiments/{experiment_id}/metrics."""

    def test_get_metrics_empty(self, client: TestClient):
        """Get metrics for experiment with no metrics returns empty list."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Empty Metrics",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Get metrics
        response = client.get(f"/experiments/{experiment_id}/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"] == []
        assert data["count"] == 0

    def test_get_metrics_with_data(self, client: TestClient):
        """Get metrics returns all metrics for experiment."""
        # Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Get Metrics Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        # Add metrics
        client.post(f"/experiments/{experiment_id}/metrics/batch", json={
            "metrics": [
                {"name": "rmse", "value": 0.75, "round_number": 1},
                {"name": "mae", "value": 0.55, "round_number": 1}
            ]
        })

        # Get metrics
        response = client.get(f"/experiments/{experiment_id}/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["metrics"]) == 2

    def test_filter_metrics_by_name(self, client: TestClient):
        """Filter metrics by name."""
        # Create experiment and add metrics
        create_response = client.post("/experiments/centralized", json={
            "name": "Filter Metrics Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        client.post(f"/experiments/{experiment_id}/metrics/batch", json={
            "metrics": [
                {"name": "rmse", "value": 0.75, "round_number": 1},
                {"name": "mae", "value": 0.55, "round_number": 1},
                {"name": "rmse", "value": 0.70, "round_number": 2}
            ]
        })

        # Filter by rmse
        response = client.get(f"/experiments/{experiment_id}/metrics?name=rmse")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert all(m["name"] == "rmse" for m in data["metrics"])


class TestDeleteMetrics:
    """Tests for DELETE /experiments/{experiment_id}/metrics."""

    def test_delete_metrics_success(self, client: TestClient):
        """Successfully delete all metrics for experiment."""
        # Create experiment and add metrics
        create_response = client.post("/experiments/centralized", json={
            "name": "Delete Metrics Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        experiment_id = create_response.json()["id"]

        client.post(f"/experiments/{experiment_id}/metrics/batch", json={
            "metrics": [
                {"name": "rmse", "value": 0.75, "round_number": 1},
                {"name": "mae", "value": 0.55, "round_number": 1}
            ]
        })

        # Delete metrics
        response = client.delete(f"/experiments/{experiment_id}/metrics")
        assert response.status_code == 204

        # Verify metrics are gone
        get_response = client.get(f"/experiments/{experiment_id}/metrics")
        assert get_response.json()["count"] == 0

    def test_delete_metrics_nonexistent_experiment(self, client: TestClient):
        """Deleting metrics for nonexistent experiment returns 404."""
        response = client.delete("/experiments/nonexistent-id/metrics")
        assert response.status_code == 404


# -----------------------------------------------------------------------------
# Test Full Experiment Lifecycle
# -----------------------------------------------------------------------------


class TestFullExperimentLifecycle:
    """Tests for complete experiment lifecycle from creation to completion."""

    def test_centralized_experiment_full_lifecycle(self, client: TestClient):
        """Test complete lifecycle: create -> start -> add metrics -> complete."""
        # 1. Create experiment
        create_response = client.post("/experiments/centralized", json={
            "name": "Full Lifecycle Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "biased_svd"
            }
        })
        assert create_response.status_code == 201
        experiment_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"

        # 2. Start experiment
        start_response = client.post(f"/experiments/{experiment_id}/start")
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "running"

        # 3. Add training metrics (simulating epoch-by-epoch)
        for epoch in range(1, 6):
            client.post(f"/experiments/{experiment_id}/metrics/batch", json={
                "metrics": [
                    {"name": "rmse", "value": 1.0 - (epoch * 0.05), "round_number": epoch},
                    {"name": "mae", "value": 0.8 - (epoch * 0.04), "round_number": epoch}
                ]
            })

        # 4. Verify metrics were added
        metrics_response = client.get(f"/experiments/{experiment_id}/metrics")
        assert metrics_response.json()["count"] == 10  # 5 epochs * 2 metrics

        # 5. Complete experiment with final metrics
        complete_response = client.post(f"/experiments/{experiment_id}/complete", json={
            "final_rmse": 0.75,
            "final_mae": 0.60,
            "training_time_seconds": 180.5
        })
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
        assert complete_response.json()["metrics"]["final_rmse"] == 0.75

        # 6. Verify final state
        final_response = client.get(f"/experiments/{experiment_id}")
        assert final_response.json()["status"] == "completed"
        assert "metrics" in final_response.json()

    def test_federated_experiment_full_lifecycle(self, client: TestClient):
        """Test federated experiment lifecycle with client metrics."""
        # 1. Create federated experiment
        create_response = client.post("/experiments/federated", json={
            "name": "Federated Lifecycle Test",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 3,
                "model_type": "biased_svd"
            },
            "n_clients": 3,
            "n_rounds": 5,
            "aggregation_strategy": "fedavg"
        })
        assert create_response.status_code == 201
        experiment_id = create_response.json()["id"]

        # 2. Start experiment
        client.post(f"/experiments/{experiment_id}/start")

        # 3. Add round metrics with client data
        for round_num in range(1, 4):
            metrics = []
            # Global metrics
            metrics.append({"name": "rmse", "value": 0.9 - (round_num * 0.05), "round_number": round_num})

            # Client-specific metrics
            for client_id in range(3):
                metrics.append({
                    "name": "client_rmse",
                    "value": 0.9 - (round_num * 0.05) + (client_id * 0.01),
                    "round_number": round_num,
                    "client_id": str(client_id)
                })

            client.post(f"/experiments/{experiment_id}/metrics/batch", json={"metrics": metrics})

        # 4. Complete experiment
        complete_response = client.post(f"/experiments/{experiment_id}/complete", json={
            "final_rmse": 0.80,
            "final_mae": 0.62,
            "training_time_seconds": 300.0
        })
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
