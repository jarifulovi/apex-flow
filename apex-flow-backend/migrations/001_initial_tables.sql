-- ==========================================
-- ApexFlow Initial Tables & Overhaul Migration
-- ==========================================

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_workflow_steps_order;
DROP INDEX IF EXISTS idx_workflow_steps_run;
DROP INDEX IF EXISTS idx_workflow_steps_locked;
DROP INDEX IF EXISTS idx_workflow_steps_queue;
DROP INDEX IF EXISTS idx_workflow_runs_parent;
DROP INDEX IF EXISTS idx_workflow_runs_dedup;
DROP INDEX IF EXISTS idx_workflow_runs_status;
DROP INDEX IF EXISTS idx_workflow_runs_project;
DROP INDEX IF EXISTS idx_workers_project_status;
DROP INDEX IF EXISTS idx_project_keys_project;
DROP INDEX IF EXISTS idx_project_keys_hash;
DROP INDEX IF EXISTS idx_projects_owner;

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS workflow_steps CASCADE;
DROP TABLE IF EXISTS workflow_runs CASCADE;
DROP TABLE IF EXISTS workflows CASCADE;
DROP TABLE IF EXISTS workers CASCADE;
DROP TABLE IF EXISTS project_keys CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

-- 1. Create the projects table (Master Multi-Tenant Boundary)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for owner lookups
CREATE INDEX idx_projects_owner ON projects (owner_id);

-- 2. Create the project_keys table
CREATE TABLE project_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    last_used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast <1ms lookup index for active project keys
CREATE UNIQUE INDEX idx_project_keys_hash ON project_keys (key_hash) WHERE status = 'active';
CREATE INDEX idx_project_keys_project ON project_keys (project_id);

-- 3. Create the workers table (Worker Registry)
CREATE TABLE workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workers_project_status ON workers (project_id, status);

-- 4. Create the workflow_runs table (Master Execution Runs)
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    deduplication_id TEXT NULL,
    parent_workflow_id UUID NULL REFERENCES workflow_runs(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_runs_project ON workflow_runs (project_id, created_at DESC);
CREATE INDEX idx_workflow_runs_status ON workflow_runs (project_id, status);
CREATE UNIQUE INDEX idx_workflow_runs_dedup ON workflow_runs (project_id, deduplication_id) WHERE deduplication_id IS NOT NULL;
CREATE INDEX idx_workflow_runs_parent ON workflow_runs (parent_workflow_id) WHERE parent_workflow_id IS NOT NULL;

-- 5. Create the workflow_steps table (Queue + Execution Checkpoints)
CREATE TABLE workflow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'queued',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    locked_until TIMESTAMPTZ NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- High-performance queue polling index (FOR UPDATE SKIP LOCKED)
CREATE INDEX idx_workflow_steps_queue ON workflow_steps (status, created_at) WHERE status = 'queued';

-- Lock recovery index for stale running steps
CREATE INDEX idx_workflow_steps_locked ON workflow_steps (status, locked_until) WHERE status = 'running';

-- Run steps lookups
CREATE INDEX idx_workflow_steps_run ON workflow_steps (workflow_run_id, created_at);
CREATE INDEX idx_workflow_steps_order ON workflow_steps (workflow_run_id, step_order);
