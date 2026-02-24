"""Check schema of old database."""

import asyncio
import asyncpg


async def check_schema():
    """Check the schema of the fedrec database."""
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="fedrec",
    )

    # Get experiments table columns
    print("=== EXPERIMENTS TABLE SCHEMA ===")
    exp_columns = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'experiments'
        ORDER BY ordinal_position
        """
    )
    for col in exp_columns:
        print(f"{col['column_name']}: {col['data_type']}")

    print("\n=== METRICS TABLE SCHEMA ===")
    metrics_columns = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'metrics'
        ORDER BY ordinal_position
        """
    )
    for col in metrics_columns:
        print(f"{col['column_name']}: {col['data_type']}")

    # Sample data
    print("\n=== SAMPLE EXPERIMENT ===")
    sample = await conn.fetchrow("SELECT * FROM experiments LIMIT 1")
    if sample:
        print(f"Columns: {sample.keys()}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
