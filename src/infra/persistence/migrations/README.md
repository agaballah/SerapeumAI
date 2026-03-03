# Migration Squashing Guide

## Overview

This directory contains versioned SQL migrations for the SerapeumAI project database schema.

## Current Status

- **Schema Version**: 14 (consolidated baseline)
- **Baseline File**: `001_baseline_v14.sql`
- **Next Migration**: Start at `016_` or higher

## Migration Strategy

### Fresh Installations

New projects run the **consolidated baseline** which applies all schema up to v14 in a single migration file.

### Existing Projects

Projects with existing databases skip the baseline (versions 1-14 already applied) and only run new migrations.

## File Structure

```
migrations/
  001_baseline_v14.sql    ← Consolidated schema (versions 1-14)
  archived/               ← Old migrations (preserved for reference)
    001_core_schema.sql
    002_hardening.sql
    ...
    015_ingestion_optimization.sql
```

## Adding New Migrations

**Naming Convention**: `{VERSION}_{description}.sql`

Example: `016_add_cost_tracking.sql`

**Template**:
```sql
-- Migration 016: Add Cost Tracking
-- Description of what this migration does

CREATE TABLE IF NOT EXISTS cost_tracking (
    id TEXT PRIMARY KEY,
    ...
);

-- Always end with version update
INSERT OR IGNORE INTO schema_version (version) VALUES (16);
```

## Migration Squashing

**When to Squash**: Every 15-20 migrations or at major version releases

**Process**: See `migration_squashing_guide.md` in the docs for detailed instructions

**Next Squash**: Recommended at migration ~030 (create `015_baseline_v30.sql`)

## Testing

Always test migrations on:
1. **Fresh database** (empty schema_version)
2. **Existing database** (with current version applied)

## References

- Migration logic: `database_manager.py::_init_db()`
- Squashing guide: See project documentation
- Archived migrations: `archived/` directory
