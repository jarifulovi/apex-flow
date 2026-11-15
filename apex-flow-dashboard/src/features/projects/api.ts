import { fetchWithAuth } from "@/lib/api";
import type {
  Project,
  ProjectCreate,
  ProjectMetrics,
  ProjectPurgeResponse,
  ProjectUpdatePayload,
  WebhookTestResponse,
} from "./types";

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

export async function updateProject(
  token: string,
  projectId: string,
  payload: ProjectUpdatePayload
): Promise<Project> {
  return fetchWithAuth<Project>(`/api/v1/projects/${projectId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function testProjectWebhook(
  token: string,
  projectId: string,
  webhookUrl: string
): Promise<WebhookTestResponse> {
  return fetchWithAuth<WebhookTestResponse>(`/api/v1/projects/${projectId}/alerts/test`, token, {
    method: "POST",
    body: JSON.stringify({ webhook_url: webhookUrl }),
  });
}

export async function purgeProjectLogs(
  token: string,
  projectId: string
): Promise<ProjectPurgeResponse> {
  return fetchWithAuth<ProjectPurgeResponse>(`/api/v1/projects/${projectId}/purge`, token, {
    method: "POST",
  });
}

export async function deleteProject(token: string, projectId: string): Promise<void> {
  await fetchWithAuth<null>(`/api/v1/projects/${projectId}`, token, {
    method: "DELETE",
  });
}
