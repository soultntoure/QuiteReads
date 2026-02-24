"""Backup the quitereads database."""

import asyncio
import asyncpg
import json
from datetime import datetime
from pathlib import Path


async def backup_database():
    """Create a JSON backup of all experiments and metrics."""

    # Connect to database
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="quitereads",
    )

    print("=== BACKING UP DATABASE ===")

    # Fetch all data
    experiments = await conn.fetch("SELECT * FROM experiments")
    metrics = await conn.fetch("SELECT * FROM metrics")

    # Convert to JSON-serializable format
    backup_data = {
        "backup_date": datetime.now().isoformat(),
        "experiments": [],
        "metrics": [],
    }

    for exp in experiments:
        exp_dict = dict(exp)
        # Convert datetime objects to strings
        exp_dict['created_at'] = exp_dict['created_at'].isoformat() if exp_dict['created_at'] else None
        exp_dict['completed_at'] = exp_dict['completed_at'].isoformat() if exp_dict['completed_at'] else None
        backup_data["experiments"].append(exp_dict)

    for metric in metrics:
        metric_dict = dict(metric)
        metric_dict['recorded_at'] = metric_dict['recorded_at'].isoformat() if metric_dict['recorded_at'] else None
        backup_data["metrics"].append(metric_dict)

    # Create backups directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    # Save backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"quitereads_backup_{timestamp}.json"

    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    print(f"\nBackup saved to: {backup_file}")
    print(f"  - {len(experiments)} experiments")
    print(f"  - {len(metrics)} metrics")
    print(f"\nYou can restore this backup later if needed.")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(backup_database())
