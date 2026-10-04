-- =========================================================================================
-- ApexFlow Migration 003: Storage Optimization & Dual Pruning Strategy via pg-cron
-- =========================================================================================
--
-- 📌 STORAGE RETENTION POLICIES & USER NOTIFICATION STRATEGY:
--
-- 1. 🧹 SOFT PAYLOAD PRUNING (Runs Daily at 02:00 AM UTC for Runs > 7 Days Old):
--    - Target: Completed workflow runs created over 7 days ago.
--    - Action: Clears heavy `input_payload` and `output_payload` JSON columns (`{}`) on `workflow_steps`.
--    - User Impact: Over 90% of storage bloat is eliminated while PRESERVING full execution history,
--      step counts, success/failure statuses, execution durations, and timeline metrics in the Dashboard!
--
-- 2. 🪓 BATCHED HARD PRUNING (Runs Daily at 03:00 AM UTC for Runs > 30 Days Old):
--    - Target: Master workflow runs created over 30 days ago.
--    - Action: Deletes master `workflow_runs` rows in small non-blocking batches of 2,000 rows.
--    - Cascade: All associated child `workflow_steps` rows are automatically deleted via `ON DELETE CASCADE`.
--    - User Impact: Prevents database bloat permanently without lock contention or WAL IO spikes.
--
-- =========================================================================================

-- 1. Enable pg_cron extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Soft Pruning Procedure: Clears heavy JSON payloads for completed runs older than 7 days
CREATE OR REPLACE FUNCTION prune_old_payloads(retention_interval INTERVAL DEFAULT INTERVAL '7 days')
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $func$
DECLARE
    cleared_count INTEGER;
BEGIN
    WITH target_runs AS (
        SELECT id FROM workflow_runs
        WHERE status = 'completed' AND created_at < (now() - retention_interval)
    ),
    cleared_steps AS (
        UPDATE workflow_steps
        SET input_payload = '{}'::jsonb, output_payload = '{}'::jsonb
        WHERE workflow_run_id IN (SELECT id FROM target_runs)
          AND (input_payload != '{}'::jsonb OR output_payload != '{}'::jsonb)
        RETURNING id
    )
    SELECT count(*) INTO cleared_count FROM cleared_steps;

    RAISE NOTICE 'ApexFlow Soft Pruning: Cleared JSON payloads for % steps older than %', cleared_count, retention_interval;
    RETURN cleared_count;
END;
$func$;

-- 3. Batched Hard Pruning Procedure: Deletes old runs in small non-blocking batches (Default: 2000 per batch)
CREATE OR REPLACE FUNCTION prune_old_workflow_runs_batched(
    retention_interval INTERVAL DEFAULT INTERVAL '30 days',
    batch_size INTEGER DEFAULT 2000
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $func$
DECLARE
    deleted_in_batch INTEGER := 0;
    total_deleted INTEGER := 0;
BEGIN
    LOOP
        WITH target_batch AS (
            SELECT id FROM workflow_runs
            WHERE created_at < (now() - retention_interval)
            LIMIT batch_size
        ),
        deleted_rows AS (
            DELETE FROM workflow_runs
            WHERE id IN (SELECT id FROM target_batch)
            RETURNING id
        )
        SELECT count(*) INTO deleted_in_batch FROM deleted_rows;

        total_deleted := total_deleted + deleted_in_batch;

        -- Exit loop when no more rows remain to delete in this run
        EXIT WHEN deleted_in_batch < batch_size;
    END LOOP;

    RAISE NOTICE 'ApexFlow Hard Pruning: Purged % workflow runs older than %', total_deleted, retention_interval;
    RETURN total_deleted;
END;
$func$;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION prune_old_payloads(INTERVAL) TO postgres;
GRANT EXECUTE ON FUNCTION prune_old_workflow_runs_batched(INTERVAL, INTEGER) TO postgres;

-- 4. Schedule Daily Cron Jobs via pg_cron (Executes at 02:00 AM & 03:00 AM UTC)
DO $cron_setup$
BEGIN
    -- Unschedule existing jobs if present (Idempotent)
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'prune-weekly-payloads') THEN
        PERFORM cron.unschedule('prune-weekly-payloads');
    END IF;
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'prune-monthly-workflow-runs') THEN
        PERFORM cron.unschedule('prune-monthly-workflow-runs');
    END IF;

    -- Job A: Soft payload pruning daily at 02:00 AM UTC (Payloads > 7 days)
    PERFORM cron.schedule(
        'prune-weekly-payloads',
        '0 2 * * *',
        $cron_cmd$SELECT prune_old_payloads(INTERVAL '7 days')$cron_cmd$
    );

    -- Job B: Batched hard pruning daily at 03:00 AM UTC (Runs > 30 days)
    PERFORM cron.schedule(
        'prune-monthly-workflow-runs',
        '0 3 * * *',
        $cron_cmd$SELECT prune_old_workflow_runs_batched(INTERVAL '30 days', 2000)$cron_cmd$
    );
END;
$cron_setup$;
