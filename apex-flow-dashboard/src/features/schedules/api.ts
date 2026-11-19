import { fetchWithAuth } from "@/lib/api";
import type {
  ScheduleCreatePayload,
  ScheduleTriggerResponse,
  ScheduleUpdatePayload,
  WorkflowSchedule,
} from "@/features/schedules/types";

export async function getSchedules(
  token: string,
  projectId: string
): Promise<WorkflowSchedule[]> {
  return fetchWithAuth<WorkflowSchedule[]>(
    `/api/v1/projects/${projectId}/schedules`,
    token
  );
}

export async function createSchedule(
  token: string,
  projectId: string,
  payload: ScheduleCreatePayload
): Promise<WorkflowSchedule> {
  return fetchWithAuth<WorkflowSchedule>(
    `/api/v1/projects/${projectId}/schedules`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function updateSchedule(
  token: string,
  projectId: string,
  scheduleId: string,
  payload: ScheduleUpdatePayload
): Promise<WorkflowSchedule> {
  return fetchWithAuth<WorkflowSchedule>(
    `/api/v1/projects/${projectId}/schedules/${scheduleId}`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function pauseSchedule(
  token: string,
  projectId: string,
  scheduleId: string
): Promise<WorkflowSchedule> {
  return fetchWithAuth<WorkflowSchedule>(
    `/api/v1/projects/${projectId}/schedules/${scheduleId}/pause`,
    token,
    { method: "POST" }
  );
}

export async function resumeSchedule(
  token: string,
  projectId: string,
  scheduleId: string
): Promise<WorkflowSchedule> {
  return fetchWithAuth<WorkflowSchedule>(
    `/api/v1/projects/${projectId}/schedules/${scheduleId}/resume`,
    token,
    { method: "POST" }
  );
}

export async function deleteSchedule(
  token: string,
  projectId: string,
  scheduleId: string
): Promise<void> {
  await fetchWithAuth<void>(
    `/api/v1/projects/${projectId}/schedules/${scheduleId}`,
    token,
    { method: "DELETE" }
  );
}

export async function triggerScheduleNow(
  token: string,
  projectId: string,
  scheduleId: string
): Promise<ScheduleTriggerResponse> {
  return fetchWithAuth<ScheduleTriggerResponse>(
    `/api/v1/projects/${projectId}/schedules/${scheduleId}/run`,
    token,
    { method: "POST" }
  );
}

