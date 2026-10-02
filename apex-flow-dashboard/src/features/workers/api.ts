import { fetchWithAuth } from "@/lib/api";
import type { Worker } from "./types";

export type { Worker };

export async function getWorkers(token: string, projectId?: string): Promise<Worker[]> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return fetchWithAuth<Worker[]>(`/api/v1/workers${query}`, token);
}
