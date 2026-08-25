import type {
  AgentRunResponse,
  ApprovalDecisionRequest,
  EmailDetail,
  EmailListResponse,
  LoginStatus,
  PendingApprovalResponse,
} from "../types";

const API_BASE = "http://localhost:8000/api";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include", // sends our login cookie with every request
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    // FastAPI errors come back as { "detail": "some message" }
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new ApiError(res.status, detail);
  }

  return res.json();
}

export const api = {
  getMe: () => apiFetch<LoginStatus>("/auth/me"),
  loginUrl: () => `${API_BASE}/auth/login`,
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

  listEmails: (maxResults = 15) =>
    apiFetch<EmailListResponse>(`/emails?max_results=${maxResults}`),

  getEmail: (id: string) => apiFetch<EmailDetail>(`/emails/${id}`),

  runAgent: (id: string) =>
    apiFetch<AgentRunResponse>(`/emails/${id}/run-agent`, { method: "POST" }),

  getPendingApproval: (id: string) =>
    apiFetch<PendingApprovalResponse>(`/emails/${id}/pending-approval`),

  approve: (id: string, decision: ApprovalDecisionRequest) =>
    apiFetch<AgentRunResponse>(`/emails/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(decision),
    }),
};

export { ApiError };