"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useActiveProject } from "@/lib/hooks";

export default function SettingsPage() {
  const { data: project } = useActiveProject();
  const { canAdmin, canEdit, activeTeamId } = useAuth();
  const queryClient = useQueryClient();
  const [parallelWorkers, setParallelWorkers] = useState(1);
  const [executionMode, setExecutionMode] = useState<"local" | "farm">("local");

  const { data: workers } = useQuery({
    queryKey: ["execution-workers"],
    queryFn: () => api.getExecutionWorkers(),
    refetchInterval: 15000,
  });

  useEffect(() => {
    if (project) {
      setParallelWorkers(project.parallel_workers);
      setExecutionMode(project.execution_mode);
    }
  }, [project]);

  const crawlMutation = useMutation({
    mutationFn: () => api.startCrawl(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteProject(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const { data: teamMembers } = useQuery({
    queryKey: ["team-members", activeTeamId],
    queryFn: () => api.listTeamMembers(activeTeamId!),
    enabled: !!activeTeamId && canAdmin,
  });

  const addMemberMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      api.addTeamMember(activeTeamId!, email, role),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["team-members", activeTeamId] }),
  });

  const settingsMutation = useMutation({
    mutationFn: () =>
      api.updateProject(project!.id, {
        parallel_workers: parallelWorkers,
        execution_mode: executionMode,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (!project) {
    return (
      <div className="card">
        <p>No project selected. Go to Workspace or Project Setup.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="mt-2 text-gray-400">Project configuration and environment</p>
      </div>

      <div className="card space-y-4">
        <h2 className="text-xl font-semibold">Active Project</h2>
        <div className="grid gap-2 text-sm">
          <div><span className="text-gray-400">ID:</span> <code>{project.id}</code></div>
          <div><span className="text-gray-400">Name:</span> {project.name}</div>
          <div><span className="text-gray-400">Base URL:</span> {project.base_url}</div>
          <div><span className="text-gray-400">Allowed domains:</span> {project.allowed_domains.join(", ")}</div>
          <div><span className="text-gray-400">Credentials:</span> {project.has_credentials ? "Configured" : "None"}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {canEdit && (
            <button
              className="btn-secondary"
              onClick={() => crawlMutation.mutate()}
              disabled={crawlMutation.isPending}
            >
              Re-run Discovery Crawl
            </button>
          )}
          {canAdmin && (
            <button
              className="btn-secondary inline-flex items-center gap-2 text-red-300"
              onClick={() => {
                if (confirm(`Delete project "${project.name}" and all its data?`)) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4" />
              Delete Project
            </button>
          )}
        </div>
      </div>

      {canAdmin && activeTeamId && (
        <div className="card space-y-4">
          <h2 className="text-xl font-semibold">Team Members</h2>
          <ul className="space-y-2 text-sm">
            {(teamMembers || []).map((member) => (
              <li key={member.id} className="flex justify-between rounded-lg bg-black/20 px-3 py-2">
                <span>{member.name} ({member.email})</span>
                <span className="badge-neutral">{member.role}</span>
              </li>
            ))}
          </ul>
          <button
            className="btn-secondary"
            onClick={() => {
              const email = prompt("Member email");
              if (email) addMemberMutation.mutate({ email, role: "member" });
            }}
          >
            Invite member
          </button>
        </div>
      )}

      {canAdmin && (
      <div className="card space-y-4">
        <h2 className="text-xl font-semibold">Parallel Test Execution</h2>
        <p className="text-sm text-gray-400">
          Run multiple Playwright specs concurrently. Use farm mode to distribute tests across Celery workers.
        </p>

        <div className="space-y-2">
          <label className="text-sm text-gray-300">Parallel workers (local mode)</label>
          <input
            type="range"
            min={1}
            max={workers?.max_parallel_workers || 8}
            value={parallelWorkers}
            onChange={(e) => setParallelWorkers(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-sm text-gray-400">{parallelWorkers} concurrent browser(s)</div>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-gray-300">Execution mode</label>
          <div className="flex gap-2">
            <button
              className={executionMode === "local" ? "btn-primary" : "btn-secondary"}
              onClick={() => setExecutionMode("local")}
            >
              Local parallel
            </button>
            <button
              className={executionMode === "farm" ? "btn-primary" : "btn-secondary"}
              onClick={() => setExecutionMode("farm")}
            >
              Browser farm
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Farm mode fans out each test to Celery workers. Scale with{" "}
            <code>docker compose up --scale worker=3</code>.
          </p>
        </div>

        {workers && (
          <div className="rounded-lg bg-gray-900/50 p-3 text-sm text-gray-400">
            Celery workers online: <span className="text-white">{workers.active_workers}</span>
          </div>
        )}

        <button
          className="btn-primary"
          onClick={() => settingsMutation.mutate()}
          disabled={settingsMutation.isPending}
        >
          Save Execution Settings
        </button>
      </div>
      )}

      <div className="card space-y-2 text-sm text-gray-400">
        <h2 className="text-xl font-semibold text-white">Environment</h2>
        <p>API URL: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</p>
        <p>OpenAI API key is configured on the backend via OPENAI_API_KEY env var.</p>
        <p>Credentials encryption uses CREDENTIALS_ENCRYPTION_KEY on the backend.</p>
      </div>
    </div>
  );
}
