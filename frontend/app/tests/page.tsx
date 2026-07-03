"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function TestsPage() {
  const { data: project } = useActiveProject();
  const queryClient = useQueryClient();

  const { data: tests } = useQuery({
    queryKey: ["tests", project?.id],
    queryFn: () => api.listTests(project!.id),
    enabled: !!project?.id,
    refetchInterval: 5000,
  });

  const runMutation = useMutation({
    mutationFn: (testIds?: string[]) => api.runTests(project!.id, testIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runs"] }),
  });

  const exportMutation = useMutation({
    mutationFn: (testId: string) => api.exportTest(testId),
    onSuccess: (content, testId) => {
      const test = tests?.find((t) => t.id === testId);
      const blob = new Blob([content as unknown as string], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${test?.name || "test"}.spec.ts`;
      a.click();
    },
  });

  if (!project) return <div className="card">No project configured.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Test Catalog</h1>
          <p className="mt-2 text-gray-400">Generated Playwright tests</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => runMutation.mutate(undefined)}
          disabled={runMutation.isPending || !tests?.length}
        >
          Run All Tests
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(var(--border))] text-left text-gray-400">
              <th className="pb-3 pr-4">Name</th>
              <th className="pb-3 pr-4">Flow</th>
              <th className="pb-3 pr-4">Status</th>
              <th className="pb-3 pr-4">Version</th>
              <th className="pb-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(tests || []).map((test) => (
              <tr key={test.id} className="border-b border-[hsl(var(--border))]/50">
                <td className="py-3 pr-4 font-medium">{test.name}</td>
                <td className="py-3 pr-4 text-gray-400">{test.flow_name || "-"}</td>
                <td className="py-3 pr-4">
                  <span className={test.status === "ready" ? "badge-success" : "badge-neutral"}>
                    {test.status}
                  </span>
                </td>
                <td className="py-3 pr-4">v{test.version}</td>
                <td className="py-3">
                  <div className="flex gap-2">
                    <button
                      className="btn-secondary text-xs"
                      onClick={() => exportMutation.mutate(test.id)}
                    >
                      Export
                    </button>
                    <button
                      className="btn-secondary text-xs"
                      onClick={() => runMutation.mutate([test.id])}
                      disabled={runMutation.isPending}
                    >
                      Run
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!tests?.length && (
          <p className="py-8 text-center text-gray-400">
            No tests generated yet. Go to Flow Map to generate tests.
          </p>
        )}
      </div>
    </div>
  );
}
