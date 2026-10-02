export interface Project {
  id: string;
  owner_id: string;
  name: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  metadata?: Record<string, unknown>;
}
