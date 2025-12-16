import asyncio

from app.infrastructure.database import get_session
from app.infrastructure.repositories.experiment_repository import ExperimentRepository
from app.core.configuration import Configuration
from app.core.experiments import CentralizedExperiment
from app.utils.types import ModelType

async def main():
    async for session in get_session():
        repo = ExperimentRepository(session)

        cfg = Configuration(
            model_type=ModelType.BIASED_SVD,
            n_factors=10,
            learning_rate=0.01,
            regularization=0.1,
            n_epochs=5,
        )
        exp = CentralizedExperiment(name="infra-test-exp", config=cfg)

        await repo.add(exp)
        fetched = await repo.get_by_id(exp.experiment_id)

        print("✅ Created experiment:", exp.experiment_id)
        print("✅ Fetched experiment:", fetched.experiment_id if fetched else None)

if __name__ == "__main__":
    asyncio.run(main())
