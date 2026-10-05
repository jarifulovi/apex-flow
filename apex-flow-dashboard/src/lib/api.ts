/**
 * ApexFlow Frontend API Client
 * Centralized fetch helper for communicating with the FastAPI backend.
 * Automatically attaches the Supabase JWT access token for authentication.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function fetchWithAuth<T>(
  endpoint: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMessage = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      const errText = await response.text().catch(() => "");
      if (errText) errorMessage = errText;
    }
    throw new ApiError(response.status, errorMessage);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

export interface PaginatedResponse<T> {
  data: T;
  totalCount: number;
}

export async function fetchWithMeta<T>(
  endpoint: string,
  token: string | null,
  options: RequestInit = {}
): Promise<PaginatedResponse<T>> {
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMessage = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      const errText = await response.text().catch(() => "");
      if (errText) errorMessage = errText;
    }
    throw new ApiError(response.status, errorMessage);
  }

  const totalCountHeader = response.headers.get("X-Total-Count");
  const parsedCount = totalCountHeader ? parseInt(totalCountHeader, 10) : NaN;

  if (response.status === 204) {
    return { data: null as T, totalCount: 0 };
  }

  const data = await response.json();
  const totalCount = !isNaN(parsedCount) ? parsedCount : (Array.isArray(data) ? data.length : 0);
  return { data, totalCount };
}
