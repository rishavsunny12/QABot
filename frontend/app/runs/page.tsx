"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function RunsPage() {
  const { data: project } = useActiveProject();

  const { data: runs } = useQuery({
    queryKey: ["runs", project?.id],
    queryFn: () => api.listRuns(project!.id),
    enabled: !!project?.id,
    refetchInterval: 5000,
  });

  if (!project) return <div className="card">No project configured.</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Run History</h1>
        <p className="mt-2 text-gray-400">Past test execution runs</p>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(var(--border))] text-left text-gray-400">
              <th className="pb-3 pr-4">Run ID</th>
              <th className="pb-3 pr-4">Status</th>
              <th className="pb-3 pr-4">Pass/Fail</th>
              <th className="pb-3 pr-4">Execution</th>
              <th className="pb-3 pr-4">Started</th>
              <th className="pb-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(runs || []).map((run) => (
              <tr key={run.id} className="border-b border-[hsl(var(--border))]/50">
                <td className="py-3 pr-4 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                <td className="py-3 pr-4">
                  <span className={run.status === "completed" ? "badge-success" : "badge-neutral"}>
                    {run.status}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  <span className="badge-success">{run.pass_count} pass</span>{" "}
                  <span className="badge-danger">{run.fail_count} fail</span>
                </td>
                <td className="py-3 pr-4 text-gray-400 text-xs">
                  {run.execution_mode || "local"}
                  {run.parallel_workers ? ` (${run.parallel_workers})` : ""}
                </td>
                <td className="py-3 pr-4 text-gray-400">
                  {run.started_at ? new Date(run.started_at).toLocaleString() : "-"}
                </td>
                <td className="py-3">
                  <Link href={`/runs/${run.id}`} className="btn-secondary text-xs">
                    View Results
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!runs?.length && (
          <p className="py-8 text-center text-gray-400">No runs yet. Run tests from the Test Catalog.</p>
        )}
      </div>
    </div>
  );
}
