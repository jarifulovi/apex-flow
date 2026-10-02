import { fetchWithAuth } from "@/lib/api";
import type { Project, ProjectCreate } from "./types";

export async function getProjects(token: string): Promise<Project[]> {
  return fetchWithAuth<Project[]>("/api/v1/projects", token);
}

export async function getOrCreateDefaultProject(token: string): Promise<Project> {
  return fetchWithAuth<Project>("/api/v1/projects/default", token);
}

export async function createProject(token: string, payload: ProjectCreate): Promise<Project> {
  return fetchWithAuth<Project>("/api/v1/projects", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getProject(token: string, projectId: string): Promise<Project> {
  return fetchWithAuth<Project>(`/api/v1/projects/${projectId}`, token);
}
