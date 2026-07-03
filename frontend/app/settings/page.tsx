"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function SettingsPage() {
  const { data: project } = useActiveProject();
  const queryClient = useQueryClient();

  const crawlMutation = useMutation({
    mutationFn: () => api.startCrawl(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (!project) {
    return (
      <div className="card">
        <p>No project configured. Go to Project Setup.</p>
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
        <h2 className="text-xl font-semibold">Project</h2>
        <div className="grid gap-2 text-sm">
          <div><span className="text-gray-400">ID:</span> <code>{project.id}</code></div>
          <div><span className="text-gray-400">Name:</span> {project.name}</div>
          <div><span className="text-gray-400">Base URL:</span> {project.base_url}</div>
          <div><span className="text-gray-400">Allowed domains:</span> {project.allowed_domains.join(", ")}</div>
          <div><span className="text-gray-400">Credentials:</span> {project.has_credentials ? "Configured" : "None"}</div>
        </div>
        <button
          className="btn-secondary"
          onClick={() => crawlMutation.mutate()}
          disabled={crawlMutation.isPending}
        >
          Re-run Discovery Crawl
        </button>
      </div>

      <div className="card space-y-2 text-sm text-gray-400">
        <h2 className="text-xl font-semibold text-white">Environment</h2>
        <p>API URL: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</p>
        <p>OpenAI API key is configured on the backend via OPENAI_API_KEY env var.</p>
        <p>Credentials encryption uses CREDENTIALS_ENCRYPTION_KEY on the backend.</p>
      </div>
    </div>
  );
}
