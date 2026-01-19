import pytest
from fastapi.testclient import TestClient
from app.api.main import app

# TestClient initialization works differently - pass app as positional arg
client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Health check should return 200 with status healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestExperimentSchemas:
    """Test experiment request/response schemas"""
    
    def test_create_centralized_request_valid(self):
        """Test that valid centralized request schema is accepted"""
        payload = {
            "name": "Test Centralized Experiment",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 10,
                "model_type": "matrix_factorization"
            }
        }
        from app.api.schemas.experiment_schemas import CreateCentralizedExperimentRequest
        req = CreateCentralizedExperimentRequest(**payload)
        assert req.name == "Test Centralized Experiment"
        assert req.config.learning_rate == 0.01
    
    def test_create_federated_request_valid(self):
        """Test that valid federated request schema is accepted"""
        payload = {
            "name": "Test Federated Experiment",
            "config": {
                "learning_rate": 0.01,
                "batch_size": 32,
                "epochs": 5,
                "model_type": "matrix_factorization"
            },
            "n_clients": 5,
            "n_rounds": 20,
            "aggregation_strategy": "FedAvg"
        }
        from app.api.schemas.experiment_schemas import CreateFederatedExperimentRequest
        req = CreateFederatedExperimentRequest(**payload)
        assert req.name == "Test Federated Experiment"
        assert req.n_clients == 5
        assert req.n_rounds == 20


class TestMetricSchemas:
    """Test metric request/response schemas"""
    
    def test_add_metric_request_valid(self):
        """Test that valid metric request is accepted"""
        payload = {
            "name": "loss",
            "value": 0.45,
            "round_number": 5,
            "client_id": "1"
        }
        from app.api.schemas.metrics_schemas import AddMetricRequest
        req = AddMetricRequest(**payload)
        assert req.name == "loss"
        assert req.value == 0.45
    
    def test_add_metrics_batch_valid(self):
        """Test that batch metrics request is accepted"""
        payload = {
            "metrics": [
                {"name": "loss", "value": 0.45, "round_number": 5},
                {"name": "accuracy", "value": 0.92, "round_number": 5}
            ]
        }
        from app.api.schemas.metrics_schemas import AddMetricsBatchRequest
        req = AddMetricsBatchRequest(**payload)
        assert len(req.metrics) == 2
