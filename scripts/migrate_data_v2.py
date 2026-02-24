"""Migrate data from old fedrec schema to new quitereads schema."""

import asyncio
import asyncpg
import json
from datetime import datetime


async def migrate_data():
    """Migrate data with schema transformation."""

    # Connect to old database
    old_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="fedrec",
    )

    # Connect to new database
    new_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="quitereads",
    )

    print("=== MIGRATING EXPERIMENTS ===")

    # Fetch old experiments
    old_experiments = await old_conn.fetch(
        """
        SELECT id, name, experiment_type, status, created_at, completed_at,
               config, final_rmse, final_mae, training_time_seconds,
               n_clients, n_rounds, aggregation_strategy
        FROM experiments
        """
    )

    migrated_experiments = 0
    for old_exp in old_experiments:
        try:
            # Transform config - old config needs to be converted to new format
            old_config = old_exp['config'] if old_exp['config'] else {}

            # Build new metrics JSON blob from old columns
            metrics_json = {}
            if old_exp['final_rmse'] is not None:
                metrics_json['final_rmse'] = old_exp['final_rmse']
            if old_exp['final_mae'] is not None:
                metrics_json['final_mae'] = old_exp['final_mae']
            if old_exp['training_time_seconds'] is not None:
                metrics_json['training_time_seconds'] = old_exp['training_time_seconds']

            # Insert into new schema
            await new_conn.execute(
                """
                INSERT INTO experiments
                (experiment_id, name, experiment_type, status, config, metrics,
                 created_at, updated_at, started_at, completed_at, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (experiment_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    metrics = EXCLUDED.metrics,
                    updated_at = EXCLUDED.updated_at,
                    completed_at = EXCLUDED.completed_at
                """,
                old_exp['id'],  # Use old id as new experiment_id
                old_exp['name'],
                old_exp['experiment_type'],
                old_exp['status'],
                json.dumps(old_config),  # config as JSON
                json.dumps(metrics_json),  # metrics as JSON
                old_exp['created_at'],
                old_exp['completed_at'] or old_exp['created_at'],  # updated_at
                old_exp['created_at'],  # started_at (assume started when created)
                old_exp['completed_at'],
                None,  # error_message
            )
            migrated_experiments += 1
            print(f"✓ Migrated experiment: {old_exp['name']} ({old_exp['id'][:8]}...)")

        except Exception as e:
            print(f"✗ Error migrating experiment {old_exp['id']}: {e}")

    print(f"\n✓ Migrated {migrated_experiments} experiments")

    print("\n=== MIGRATING METRICS ===")

    # Fetch old metrics
    old_metrics = await old_conn.fetch(
        """
        SELECT id, experiment_id, name, value, context, round_number, recorded_at
        FROM metrics
        ORDER BY experiment_id, round_number, id
        """
    )

    migrated_metrics = 0
    skipped = 0

    for old_metric in old_metrics:
        try:
            # Check if the experiment exists in new database
            exp_exists = await new_conn.fetchval(
                "SELECT 1 FROM experiments WHERE experiment_id = $1",
                old_metric['experiment_id']
            )

            if not exp_exists:
                skipped += 1
                continue

            # Generate a UUID for the metric
            import uuid
            metric_id = str(uuid.uuid4())

            # Map old metric name to new format
            metric_name = old_metric['name'].lower()

            # Insert into new metrics table
            await new_conn.execute(
                """
                INSERT INTO metrics
                (metric_id, experiment_id, epoch_or_round, metric_name, metric_value, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                metric_id,
                old_metric['experiment_id'],
                old_metric['round_number'] if old_metric['round_number'] is not None else 0,
                metric_name,
                old_metric['value'],
                old_metric['recorded_at'],
            )
            migrated_metrics += 1

            if migrated_metrics % 100 == 0:
                print(f"  Progress: {migrated_metrics} metrics migrated...")

        except Exception as e:
            print(f"✗ Error migrating metric {old_metric['id']}: {e}")
            skipped += 1

    print(f"\n✓ Migrated {migrated_metrics} metrics")
    if skipped > 0:
        print(f"  (Skipped {skipped} metrics from non-existent experiments)")

    # Verify migration
    new_exp_count = await new_conn.fetchval("SELECT COUNT(*) FROM experiments")
    new_metrics_count = await new_conn.fetchval("SELECT COUNT(*) FROM metrics")

    print(f"\n{'='*50}")
    print(f"MIGRATION SUMMARY")
    print(f"{'='*50}")
    print(f"Old database (fedrec):")
    print(f"  - {len(old_experiments)} experiments")
    print(f"  - {len(old_metrics)} metrics")
    print(f"\nNew database (quitereads):")
    print(f"  - {new_exp_count} experiments")
    print(f"  - {new_metrics_count} metrics")
    print(f"\n✓ Migration complete!")

    await old_conn.close()
    await new_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_data())
