import asyncio
import pytest

from app.infrastructure.database import get_session
from app.infrastructure.repositories.experiment_repository import ExperimentRepository
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment
from app.utils.types import ModelType

@pytest.mark.asyncio
async def test_experiment_add_and_get():
    async for session in get_session():
        repo = ExperimentRepository(session)
        cfg = Configuration(
            model_type=ModelType.BIASED_SVD,
            n_factors=10,
            learning_rate=0.01,
            regularization=0.1,
            n_epochs=5,
        )
        exp = CentralizedExperiment(name="test-exp", config=cfg)

        await repo.add(exp)
        fetched = await repo.get_by_id(exp.experiment_id)

        assert fetched is not None
        assert fetched.name == "test-exp"
