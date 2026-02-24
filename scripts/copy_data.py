"""Copy data from fedrec to quitereads database (same schema)."""

import asyncio
import asyncpg


async def copy_data():
    """Copy all data from fedrec to quitereads."""

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

    print("=== COPYING EXPERIMENTS ===")

    # Copy experiments
    experiments = await old_conn.fetch("SELECT * FROM experiments")

    copied_experiments = 0
    for exp in experiments:
        try:
            await new_conn.execute(
                """
                INSERT INTO experiments
                (id, name, experiment_type, status, created_at, completed_at,
                 config, final_rmse, final_mae, training_time_seconds,
                 n_clients, n_rounds, aggregation_strategy)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    final_rmse = EXCLUDED.final_rmse,
                    final_mae = EXCLUDED.final_mae,
                    training_time_seconds = EXCLUDED.training_time_seconds
                """,
                exp['id'],
                exp['name'],
                exp['experiment_type'],
                exp['status'],
                exp['created_at'],
                exp['completed_at'],
                exp['config'],
                exp['final_rmse'],
                exp['final_mae'],
                exp['training_time_seconds'],
                exp['n_clients'],
                exp['n_rounds'],
                exp['aggregation_strategy'],
            )
            copied_experiments += 1
            print(f"  + {exp['name']} ({exp['id'][:8]}...)")
        except Exception as e:
            print(f"  x Error copying experiment {exp['id']}: {e}")

    print(f"\nCopied {copied_experiments}/{len(experiments)} experiments")

    print("\n=== COPYING METRICS ===")

    # Copy metrics
    metrics = await old_conn.fetch("SELECT * FROM metrics")

    copied_metrics = 0
    for metric in metrics:
        try:
            await new_conn.execute(
                """
                INSERT INTO metrics
                (id, experiment_id, name, value, context, round_number, client_id, recorded_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                """,
                metric['id'],
                metric['experiment_id'],
                metric['name'],
                metric['value'],
                metric['context'],
                metric['round_number'],
                metric['client_id'],
                metric['recorded_at'],
            )
            copied_metrics += 1

            if copied_metrics % 100 == 0:
                print(f"  Progress: {copied_metrics}/{len(metrics)} metrics...")

        except Exception as e:
            print(f"  x Error copying metric {metric['id']}: {e}")

    print(f"\nCopied {copied_metrics}/{len(metrics)} metrics")

    # Verify
    new_exp_count = await new_conn.fetchval("SELECT COUNT(*) FROM experiments")
    new_metrics_count = await new_conn.fetchval("SELECT COUNT(*) FROM metrics")

    print(f"\n{'='*60}")
    print(f"MIGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"quitereads database now contains:")
    print(f"  - {new_exp_count} experiments")
    print(f"  - {new_metrics_count} metrics")
    print(f"\nAll your experiment data has been preserved!")

    await old_conn.close()
    await new_conn.close()


if __name__ == "__main__":
    asyncio.run(copy_data())
