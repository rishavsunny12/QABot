const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res.text() as T;
}

export const api = {
  getAuthConfig: () => request<import("./types").AuthConfig>("/api/auth/config"),
  getMe: () => request<import("./types").AuthUser>("/api/auth/me"),
  devLogin: (email: string, name?: string) =>
    request<import("./types").AuthUser>("/api/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email, name }),
    }),
  logout: () => request<{ status: string }>("/api/auth/logout", { method: "POST" }),
  listTeams: () => request<import("./types").TeamMembership[]>("/api/teams"),
  createTeam: (name: string) =>
    request<{ id: string; name: string; slug: string; role: string }>("/api/teams", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  listTeamMembers: (teamId: string) =>
    request<import("./types").TeamMember[]>(`/api/teams/${teamId}/members`),
  addTeamMember: (teamId: string, email: string, role: string) =>
    request<import("./types").TeamMember>(`/api/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),
  listProjects: (teamId?: string | null) =>
    request<import("./types").Project[]>(
      teamId ? `/api/projects?team_id=${encodeURIComponent(teamId)}` : "/api/projects"
    ),
  getProject: (id: string) => request<import("./types").Project>(`/api/projects/${id}`),
  createProject: (data: Record<string, unknown>) =>
    request<import("./types").Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateProject: (id: string, data: Record<string, unknown>) =>
    request<import("./types").Project>(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteProject: (id: string) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),
  startCrawl: (id: string) =>
    request<{ job_id: string; status: string }>(`/api/projects/${id}/crawl`, { method: "POST" }),
  crawlStatus: (id: string) =>
    request<import("./types").CrawlStatus>(`/api/projects/${id}/crawl-status`),
  listPages: (id: string) => request<import("./types").Page[]>(`/api/projects/${id}/pages`),
  listFlows: (id: string) => request<import("./types").Flow[]>(`/api/projects/${id}/flows`),
  flowGraph: (id: string) => request<import("./types").FlowGraph>(`/api/projects/${id}/flow-graph`),
  generateTests: (id: string, flowIds?: string[]) =>
    request<{ job_id: string }>(`/api/projects/${id}/generate-tests`, {
      method: "POST",
      body: JSON.stringify({ flow_ids: flowIds }),
    }),
  listTests: (id: string) => request<import("./types").GeneratedTest[]>(`/api/projects/${id}/tests`),
  exportTest: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tests/${id}/export`, {
      method: "POST",
      credentials: "include",
    });
    return res.text();
  },
  runTests: (id: string, testIds?: string[]) =>
    request<{ job_id: string }>(`/api/projects/${id}/run-tests`, {
      method: "POST",
      body: JSON.stringify({ test_ids: testIds }),
    }),
  listRuns: (id: string) => request<import("./types").TestRun[]>(`/api/projects/${id}/runs`),
  getRun: (id: string) => request<import("./types").TestRun>(`/api/runs/${id}`),
  getRunResults: (id: string) => request<import("./types").TestRunResult[]>(`/api/runs/${id}/results`),
  getResult: (id: string) => request<import("./types").TestRunResult>(`/api/results/${id}`),
  healingSuggestions: (resultId: string) =>
    request<import("./types").HealingSuggestion[]>(`/api/results/${resultId}/healing-suggestions`),
  approveHealing: (id: string) =>
    request<import("./types").HealingSuggestion>(`/api/healing-suggestions/${id}/approve`, {
      method: "POST",
    }),
  rejectHealing: (id: string) =>
    request<import("./types").HealingSuggestion>(`/api/healing-suggestions/${id}/reject`, {
      method: "POST",
    }),
  listSchedules: (projectId: string) =>
    request<import("./types").TestSchedule[]>(`/api/projects/${projectId}/schedules`),
  createSchedule: (projectId: string, data: Record<string, unknown>) =>
    request<import("./types").TestSchedule>(`/api/projects/${projectId}/schedules`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateSchedule: (id: string, data: Record<string, unknown>) =>
    request<import("./types").TestSchedule>(`/api/schedules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteSchedule: (id: string) =>
    request<void>(`/api/schedules/${id}`, { method: "DELETE" }),
  toggleSchedule: (id: string) =>
    request<import("./types").TestSchedule>(`/api/schedules/${id}/toggle`, { method: "POST" }),
  captureVisualBaselines: (projectId: string) =>
    request<import("./types").VisualBaseline[]>(
      `/api/projects/${projectId}/visual-baselines/capture`,
      { method: "POST" }
    ),
  listVisualBaselines: (projectId: string) =>
    request<import("./types").VisualBaseline[]>(`/api/projects/${projectId}/visual-baselines`),
  startVisualRun: (projectId: string, thresholdPercent?: number) =>
    request<{ job_id: string }>(`/api/projects/${projectId}/visual-regression/run`, {
      method: "POST",
      body: JSON.stringify({ threshold_percent: thresholdPercent ?? 1.0 }),
    }),
  listVisualRuns: (projectId: string) =>
    request<import("./types").VisualComparisonRun[]>(
      `/api/projects/${projectId}/visual-regression/runs`
    ),
  getVisualRun: (runId: string) =>
    request<import("./types").VisualComparisonRun>(`/api/visual-regression/runs/${runId}`),
  visualArtifactUrl: (resultId: string, type: "baseline" | "current" | "diff") =>
    `${API_URL}/api/visual-regression/results/${resultId}/artifacts/${type}`,
  screenshotUrl: (projectId: string, pageId: string) =>
    `${API_URL}/api/projects/${projectId}/screenshots/${pageId}`,
  artifactUrl: (resultId: string, type: string) =>
    `${API_URL}/api/results/${resultId}/artifacts/${type}`,
  getExecutionWorkers: () =>
    request<import("./types").ExecutionWorkers>("/api/execution/workers"),
  listBillingPlans: () => request<import("./types").BillingPlan[]>("/api/billing/plans"),
  getTeamBilling: (teamId: string) =>
    request<import("./types").TeamBilling>(`/api/billing/teams/${teamId}`),
  changeTeamPlan: (teamId: string, planSlug: string) =>
    request<import("./types").TeamBilling>(`/api/billing/teams/${teamId}/change-plan`, {
      method: "POST",
      body: JSON.stringify({ plan_slug: planSlug }),
    }),
};

export { API_URL };
