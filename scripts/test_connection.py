"""Test database connection and verify data."""

import asyncio
from app.infrastructure.database import get_session_factory
from app.infrastructure.repositories.experiment_repository import ExperimentRepository


async def test_connection():
    """Test database connection and data access."""
    try:
        factory = get_session_factory()

        async with factory() as session:
            repo = ExperimentRepository(session)
            exps = await repo.get_all()

            print(f"Database connection successful!")
            print(f"Found {len(exps)} experiments in database")

            if exps:
                print(f"\nRecent experiments:")
                for exp in exps[:5]:
                    print(f"  - {exp.name} ({exp.experiment_type}) - {exp.status}")

            return True

    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
