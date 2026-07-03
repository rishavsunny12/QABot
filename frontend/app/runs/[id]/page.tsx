"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function RunDetailPage({ params }: { params: { id: string } }) {
  const { data: run } = useQuery({
    queryKey: ["run", params.id],
    queryFn: () => api.getRun(params.id),
  });

  const { data: results } = useQuery({
    queryKey: ["run-results", params.id],
    queryFn: () => api.getRunResults(params.id),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <div>
        <Link href="/runs" className="text-sm text-blue-400 hover:underline">
          ← Back to Run History
        </Link>
        <h1 className="mt-2 text-3xl font-bold">Run Results</h1>
        {run && (
          <p className="mt-2 text-gray-400">
            {run.pass_count} passed, {run.fail_count} failed — {run.status}
            {run.execution_mode && (
              <span className="ml-2 text-xs">
                ({run.execution_mode} mode
                {run.parallel_workers ? `, ${run.parallel_workers} workers` : ""})
              </span>
            )}
          </p>
        )}
      </div>

      <div className="space-y-3">
        {(results || []).map((result) => (
          <div key={result.id} className="card flex items-center justify-between">
            <div>
              <div className="font-medium">{result.test_name}</div>
              <div className="mt-1 flex gap-2 text-xs">
                <span className={result.status === "passed" ? "badge-success" : "badge-danger"}>
                  {result.status}
                </span>
                {result.duration_ms != null && (
                  <span className="badge-neutral">{result.duration_ms}ms</span>
                )}
                {result.failure_category && (
                  <span className="badge-warning">{result.failure_category}</span>
                )}
              </div>
            </div>
            {result.status === "failed" && (
              <Link href={`/failures/${result.id}`} className="btn-secondary text-xs">
                View Failure
              </Link>
            )}
          </div>
        ))}
        {!results?.length && <div className="card text-gray-400">Loading results...</div>}
      </div>
    </div>
  );
}
