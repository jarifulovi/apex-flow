import { fetchWithAuth } from "@/lib/api";

export interface ProjectKey {
  id: string;
  name: string;
  key_prefix: string;
  status: "active" | "revoked";
  last_used_at: string | null;
  created_at: string;
}

export interface ProjectKeyCreated extends ProjectKey {
  raw_key: string;
}

export async function getProjectKeys(token: string): Promise<ProjectKey[]> {
  return fetchWithAuth<ProjectKey[]>("/api/v1/keys", token);
}

export async function createProjectKey(token: string, name: string): Promise<ProjectKeyCreated> {
  return fetchWithAuth<ProjectKeyCreated>("/api/v1/keys", token, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function deleteProjectKey(token: string, keyId: string): Promise<ProjectKey> {
  return fetchWithAuth<ProjectKey>(`/api/v1/keys/${keyId}`, token, {
    method: "DELETE",
  });
}
