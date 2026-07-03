const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
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
  listProjects: () => request<import("./types").Project[]>("/api/projects"),
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
    const res = await fetch(`${API_URL}/api/tests/${id}/export`, { method: "POST" });
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
  deleteProject: (id: string) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),
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
  screenshotUrl: (projectId: string, pageId: string) =>
    `${API_URL}/api/projects/${projectId}/screenshots/${pageId}`,
  artifactUrl: (resultId: string, type: string) =>
    `${API_URL}/api/results/${resultId}/artifacts/${type}`,
};

export { API_URL };
