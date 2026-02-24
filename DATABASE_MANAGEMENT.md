# Database Management Guide

## Current Setup

**Database Name:** `quitereads`
**Connection:** `postgresql+asyncpg://postgres:postgres@localhost:5432/quitereads`
**Configuration:** `app/infrastructure/database.py`

## Your Data

Your database currently contains:
- **29 experiments** (all successfully migrated from old `fedrec` database)
- **771 metrics** (complete training history preserved)

All historical experiments and metrics have been preserved during the project rename.

## Backup & Restore

### Creating a Backup

**Recommended:** Create backups before:
- Running new experiments
- Making schema changes
- Major refactoring

```bash
# Create a backup (stored in backups/ directory)
uv run python scripts/backup_database.py
```

Backups are saved as JSON files with timestamp: `backups/quitereads_backup_YYYYMMDD_HHMMSS.json`

### Automatic Backup Schedule

Consider creating backups:
- **Daily:** Before starting work
- **Before experiments:** Before running long-running experiments
- **After major milestones:** After completing significant experiment runs

### Backup Storage

- Local backups: `backups/` directory (git-ignored)
- **Recommended:** Also back up to cloud storage (Google Drive, Dropbox, etc.)

## Database Operations

### Viewing Data

```bash
# Connect to database
psql -U postgres -d quitereads

# View experiments
SELECT id, name, status, created_at FROM experiments;

# View metrics count per experiment
SELECT experiment_id, COUNT(*) FROM metrics GROUP BY experiment_id;

# Exit
\q
```

### Running Migrations

When you modify models in `app/infrastructure/models.py`:

```bash
# 1. Create migration
uv run alembic revision --autogenerate -m "description of changes"

# 2. Review migration file in alembic/versions/

# 3. Apply migration
uv run alembic upgrade head
```

### Resetting Database (Development Only)

**WARNING:** This deletes all data!

```bash
# Drop and recreate database
uv run python scripts/reset_database.py  # (create this if needed)

# Or manually:
# 1. Drop database
psql -U postgres -c "DROP DATABASE quitereads;"

# 2. Recreate
uv run python scripts/create_db.py

# 3. Run migrations
uv run alembic upgrade head
```

## Data Integrity

### Ensuring No Data Loss

1. **Regular Backups**: Run backup script weekly or before important work
2. **Git Commits**: Commit database migrations to version control
3. **Test Database**: Use separate test database for development
4. **Foreign Keys**: Schema enforces referential integrity (metrics → experiments)

### Verifying Data

```bash
# Check experiment count
psql -U postgres -d quitereads -c "SELECT COUNT(*) FROM experiments;"

# Check metrics count
psql -U postgres -d quitereads -c "SELECT COUNT(*) FROM metrics;"

# Check for orphaned metrics (should return 0)
psql -U postgres -d quitereads -c "
SELECT COUNT(*) FROM metrics m
WHERE NOT EXISTS (SELECT 1 FROM experiments e WHERE e.id = m.experiment_id);
"
```

## Troubleshooting

### Database Connection Errors

If you see `database "quitereads" does not exist`:
```bash
uv run python scripts/create_db.py
uv run alembic upgrade head
```

### Migration Conflicts

If migrations fail:
```bash
# Check current migration version
uv run alembic current

# View migration history
uv run alembic history

# Downgrade one version
uv run alembic downgrade -1

# Then try upgrade again
uv run alembic upgrade head
```

### Data Recovery

To restore from backup:
```bash
uv run python scripts/restore_database.py backups/quitereads_backup_YYYYMMDD_HHMMSS.json
```

(Note: Create this script if needed - it's the inverse of backup_database.py)

## Best Practices

1. **Always backup before migrations**
2. **Test migrations on a copy first** (create test database)
3. **Keep backups for at least 30 days**
4. **Document schema changes** in migration commit messages
5. **Monitor database size** (PostgreSQL can grow large with many metrics)
6. **Clean up old experiments** if needed (archive to JSON first)

## Monitoring Database Size

```bash
# Check database size
psql -U postgres -c "
SELECT pg_size_pretty(pg_database_size('quitereads'));
"

# Check table sizes
psql -U postgres -d quitereads -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::text)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;
"
```

## Emergency Contacts

If you encounter critical database issues:
1. **Don't panic** - you have backups
2. **Check backups/** directory
3. **Review recent migrations** in `alembic/versions/`
4. **Consult this guide** for recovery procedures

---

**Last Updated:** 2026-02-24
**Database Version:** quitereads v1.0
**Total Records:** 29 experiments, 771 metrics
