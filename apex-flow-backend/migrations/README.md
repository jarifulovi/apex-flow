# SQL Migrations Directory

Place raw `.sql` files here to be executed sequentially against the PostgreSQL database / Supabase SQL Editor.

## Migration Index
- `001_initial_tables.sql`: Initial schema setup for projects, project_keys, workers, workflow_runs, and workflow_steps.
- `002_admin_confirm_functions.sql`: Helper functions for user admin confirmation.
- `003_pg_cron_pruning_strategy.sql`: Enables `pg_cron`, creates `prune_old_payloads()` (soft payload clearing > 7 days) and `prune_old_workflow_runs_batched()` (batched hard delete > 30 days), and schedules daily cron jobs (`0 2 * * *` and `0 3 * * *`).
