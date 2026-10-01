// Dummy data for Project Keys — aligned to backend ProjectKeyResponse schema

export type KeyStatus = "active" | "revoked";

export interface ProjectKey {
  id: string;
  user_id: string;
  name: string;
  key_prefix: string;
  status: KeyStatus;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export const DUMMY_PROJECT_KEYS: ProjectKey[] = [
  {
    id: "key-001-uuid",
    user_id: "user-uuid-1",
    name: "Production Worker",
    key_prefix: "af3x",
    status: "active",
    last_used_at: "2026-09-30T10:03:45Z",
    created_at: "2026-09-01T09:00:00Z",
    updated_at: "2026-09-30T10:03:45Z",
  },
  {
    id: "key-002-uuid",
    user_id: "user-uuid-1",
    name: "Staging Worker",
    key_prefix: "bf9q",
    status: "active",
    last_used_at: "2026-09-28T14:30:00Z",
    created_at: "2026-09-15T11:00:00Z",
    updated_at: "2026-09-28T14:30:00Z",
  },
  {
    id: "key-003-uuid",
    user_id: "user-uuid-1",
    name: "Legacy CI Key",
    key_prefix: "cx2m",
    status: "revoked",
    last_used_at: "2026-09-10T08:15:00Z",
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-09-20T00:00:00Z",
  },
];
