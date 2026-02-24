"""Migrate data from fedrec database to quitereads database."""

import asyncio
import asyncpg


async def check_and_migrate():
    """Check old database and migrate data if it exists."""

    # Connect to postgres to check if old database exists
    admin_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="postgres",
    )

    # Check if old database exists
    old_db_exists = await admin_conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'fedrec'"
    )

    if not old_db_exists:
        print("Old database 'fedrec' does not exist. Nothing to migrate.")
        await admin_conn.close()
        return

    print("Found old database 'fedrec'. Checking for data...")

    # Connect to old database
    old_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="fedrec",
    )

    # Check for experiments
    experiment_count = await old_conn.fetchval(
        "SELECT COUNT(*) FROM experiments"
    ) if await old_conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'experiments')"
    ) else 0

    # Check for metrics
    metrics_count = await old_conn.fetchval(
        "SELECT COUNT(*) FROM metrics"
    ) if await old_conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'metrics')"
    ) else 0

    print(f"Found {experiment_count} experiments and {metrics_count} metrics in old database.")

    if experiment_count == 0 and metrics_count == 0:
        print("No data to migrate.")
        await old_conn.close()
        await admin_conn.close()
        return

    # Connect to new database
    new_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="quitereads",
    )

    print("\nMigrating data to 'quitereads' database...")

    # Migrate experiments
    if experiment_count > 0:
        experiments = await old_conn.fetch(
            """
            SELECT experiment_id, name, experiment_type, status, config, metrics,
                   created_at, updated_at, started_at, completed_at, error_message
            FROM experiments
            """
        )
        migrated = 0
        for exp in experiments:
            try:
                await new_conn.execute(
                    """
                    INSERT INTO experiments
                    (experiment_id, name, experiment_type, status, config, metrics,
                     created_at, updated_at, started_at, completed_at, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (experiment_id) DO NOTHING
                    """,
                    exp[0],  # experiment_id
                    exp[1],  # name
                    exp[2],  # experiment_type
                    exp[3],  # status
                    exp[4],  # config
                    exp[5],  # metrics
                    exp[6],  # created_at
                    exp[7],  # updated_at
                    exp[8],  # started_at
                    exp[9],  # completed_at
                    exp[10], # error_message
                )
                migrated += 1
            except Exception as e:
                print(f"Error migrating experiment: {e}")

        print(f"✓ Migrated {migrated} experiments")

    # Migrate metrics
    if metrics_count > 0:
        metrics = await old_conn.fetch(
            """
            SELECT metric_id, experiment_id, epoch_or_round, metric_name, metric_value, timestamp
            FROM metrics
            """
        )
        migrated_metrics = 0
        for metric in metrics:
            try:
                await new_conn.execute(
                    """
                    INSERT INTO metrics
                    (metric_id, experiment_id, epoch_or_round, metric_name, metric_value, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (metric_id) DO NOTHING
                    """,
                    metric[0],  # metric_id
                    metric[1],  # experiment_id
                    metric[2],  # epoch_or_round
                    metric[3],  # metric_name
                    metric[4],  # metric_value
                    metric[5],  # timestamp
                )
                migrated_metrics += 1
            except Exception as e:
                print(f"Error migrating metric: {e}")

        print(f"✓ Migrated {migrated_metrics} metrics")

    # Verify migration
    new_exp_count = await new_conn.fetchval("SELECT COUNT(*) FROM experiments")
    new_metrics_count = await new_conn.fetchval("SELECT COUNT(*) FROM metrics")

    print(f"\nMigration complete!")
    print(f"New database now has: {new_exp_count} experiments and {new_metrics_count} metrics")

    await old_conn.close()
    await new_conn.close()
    await admin_conn.close()


if __name__ == "__main__":
    asyncio.run(check_and_migrate())
