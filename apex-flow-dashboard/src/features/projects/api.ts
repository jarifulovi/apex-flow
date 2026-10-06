import { fetchWithAuth } from "@/lib/api";
import type { Project, ProjectCreate, ProjectMetrics } from "./types";

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

export async function getProjectMetrics(token: string, projectId: string): Promise<ProjectMetrics> {
  return fetchWithAuth<ProjectMetrics>(`/api/v1/projects/${projectId}/metrics`, token);
}

export async function getProjectOverview(token: string, projectId: string): Promise<any> {
  return fetchWithAuth<any>(`/api/v1/projects/${projectId}/overview`, token);
}
