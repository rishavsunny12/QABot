"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function FailurePage({ params }: { params: { resultId: string } }) {
  const queryClient = useQueryClient();

  const { data: result } = useQuery({
    queryKey: ["result", params.resultId],
    queryFn: () => api.getResult(params.resultId),
  });

  const { data: suggestions } = useQuery({
    queryKey: ["healing", params.resultId],
    queryFn: () => api.healingSuggestions(params.resultId),
    enabled: !!result && result.status === "failed",
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.approveHealing(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["healing"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.rejectHealing(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["healing"] }),
  });

  if (!result) return <div className="card">Loading...</div>;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Link href={`/runs/${result.test_run_id}`} className="text-sm text-blue-400 hover:underline">
          ← Back to Run
        </Link>
        <h1 className="mt-2 text-3xl font-bold">Failure Details</h1>
        <p className="mt-2 text-gray-400">{result.test_name}</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h2 className="mb-3 font-semibold">Screenshot</h2>
          {result.screenshot_path ? (
            <img
              src={api.artifactUrl(result.id, "screenshot")}
              alt="Failure screenshot"
              className="rounded-lg border border-[hsl(var(--border))]"
            />
          ) : (
            <p className="text-gray-400">No screenshot available</p>
          )}
        </div>

        <div className="card space-y-4">
          <div>
            <h2 className="mb-2 font-semibold">Status</h2>
            <span className="badge-danger">{result.status}</span>
            {result.failure_category && (
              <span className="ml-2 badge-warning">{result.failure_category}</span>
            )}
          </div>

          <div>
            <h2 className="mb-2 font-semibold">AI Summary</h2>
            <pre className="whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-sm text-gray-300">
              {result.ai_summary || "No AI summary available (set OPENAI_API_KEY for AI analysis)"}
            </pre>
          </div>

          <div>
            <h2 className="mb-2 font-semibold">Raw Error</h2>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-xs text-red-300">
              {result.error_message || "No error message"}
            </pre>
          </div>

          {result.trace_path && (
            <a
              href={api.artifactUrl(result.id, "trace")}
              className="btn-secondary inline-block"
              download
            >
              Download Trace
            </a>
          )}
        </div>
      </div>

      {(suggestions || []).map((s) => (
        <div key={s.id} className="card space-y-3">
          <h2 className="font-semibold">Selector Healing Suggestion</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-400">Failed selector</div>
              <code className="mt-1 block rounded bg-black/30 p-2 text-xs">{s.failed_selector}</code>
            </div>
            <div>
              <div className="text-gray-400">Suggested selector</div>
              <code className="mt-1 block rounded bg-black/30 p-2 text-xs text-green-300">
                {s.suggested_selector}
              </code>
            </div>
          </div>
          <p className="text-sm text-gray-400">{s.rationale}</p>
          <div className="flex gap-2">
            {s.approved === null ? (
              <>
                <button
                  className="btn-primary"
                  onClick={() => approveMutation.mutate(s.id)}
                  disabled={approveMutation.isPending}
                >
                  Approve
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => rejectMutation.mutate(s.id)}
                  disabled={rejectMutation.isPending}
                >
                  Reject
                </button>
              </>
            ) : (
              <span className={s.approved ? "badge-success" : "badge-neutral"}>
                {s.approved ? "Approved" : "Rejected"}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
