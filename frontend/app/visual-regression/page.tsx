"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Play, Camera } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function VisualRegressionPage() {
  const { data: project } = useActiveProject();
  const queryClient = useQueryClient();
  const [threshold, setThreshold] = useState(1.0);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: baselines } = useQuery({
    queryKey: ["visual-baselines", project?.id],
    queryFn: () => api.listVisualBaselines(project!.id),
    enabled: !!project?.id,
  });

  const { data: runs } = useQuery({
    queryKey: ["visual-runs", project?.id],
    queryFn: () => api.listVisualRuns(project!.id),
    enabled: !!project?.id,
    refetchInterval: 5000,
  });

  const { data: runDetail } = useQuery({
    queryKey: ["visual-run", selectedRunId],
    queryFn: () => api.getVisualRun(selectedRunId!),
    enabled: !!selectedRunId,
    refetchInterval: selectedRunId ? 5000 : false,
  });

  const captureMutation = useMutation({
    mutationFn: () => api.captureVisualBaselines(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["visual-baselines"] }),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runVisualRegression(project!.id, threshold),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["visual-runs"] }),
  });

  if (!project) {
    return <div className="card">Select a project to use visual regression.</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Visual Regression</h1>
        <p className="mt-2 text-gray-400">
          Compare page screenshots against baselines captured from discovery crawl.
        </p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <button
          className="btn-primary inline-flex items-center gap-2"
          onClick={() => captureMutation.mutate()}
          disabled={captureMutation.isPending}
        >
          <Camera className="h-4 w-4" />
          Capture Baselines from Crawl
        </button>
        <div>
          <label className="mb-1 block text-sm text-gray-400">Diff threshold (%)</label>
          <input
            className="input w-32"
            type="number"
            min={0}
            max={100}
            step={0.1}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </div>
        <button
          className="btn-secondary inline-flex items-center gap-2"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending || !baselines?.length}
        >
          <Play className="h-4 w-4" />
          Run Comparison
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold">Baselines ({baselines?.length ?? 0})</h2>
          <div className="space-y-2">
            {(baselines || []).map((b) => (
              <div key={b.id} className="rounded-lg border border-[hsl(var(--border))] p-3 text-sm">
                <div className="font-medium">{b.label || b.url}</div>
                <div className="truncate text-xs text-gray-400">{b.url}</div>
              </div>
            ))}
            {!baselines?.length && (
              <p className="text-gray-400">Run a crawl, then capture baselines.</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 text-xl font-semibold">Comparison Runs</h2>
          <div className="space-y-2">
            {(runs || []).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => setSelectedRunId(run.id)}
                className={`flex w-full items-center justify-between rounded-lg border p-3 text-left text-sm ${
                  selectedRunId === run.id
                    ? "border-blue-500/50 bg-blue-600/10"
                    : "border-[hsl(var(--border))] hover:bg-white/5"
                }`}
              >
                <span className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  {new Date(run.started_at).toLocaleString()}
                </span>
                <span>
                  <span className="badge-success">{run.pass_count} pass</span>{" "}
                  <span className="badge-danger">{run.fail_count} fail</span>
                </span>
              </button>
            ))}
            {!runs?.length && <p className="text-gray-400">No comparison runs yet.</p>}
          </div>
        </div>
      </div>

      {runDetail && (
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold">Run Results</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {runDetail.results?.map((result) => (
              <div
                key={result.id}
                className="rounded-lg border border-[hsl(var(--border))] p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="truncate text-sm font-medium">{result.page_url}</span>
                  <span className={result.status === "passed" ? "badge-success" : "badge-danger"}>
                    {result.diff_percent.toFixed(2)}%
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {(["baseline", "current", "diff"] as const).map((type) => (
                    <div key={type}>
                      <div className="mb-1 text-xs capitalize text-gray-400">{type}</div>
                      {result.current_path || type === "baseline" ? (
                        <img
                          src={api.visualArtifactUrl(result.id, type)}
                          alt={type}
                          className="h-24 w-full rounded border border-[hsl(var(--border))] object-cover object-top bg-black/40"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="flex h-24 items-center justify-center rounded border border-dashed border-[hsl(var(--border))] text-xs text-gray-500">
                          N/A
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
