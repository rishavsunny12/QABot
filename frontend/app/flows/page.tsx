"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function FlowsPage() {
  const { data: project } = useActiveProject();
  const queryClient = useQueryClient();

  const { data: graph } = useQuery({
    queryKey: ["flow-graph", project?.id],
    queryFn: () => api.flowGraph(project!.id),
    enabled: !!project?.id,
  });

  const initialNodes = useMemo(
    () =>
      (graph?.nodes || []).map((n, i) => ({
        id: n.id,
        position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 120 },
        data: { label: n.label },
      })),
    [graph?.nodes]
  );

  const initialEdges = useMemo(
    () =>
      (graph?.edges || []).map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    [graph?.edges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const generateMutation = useMutation({
    mutationFn: (flowIds?: string[]) => api.generateTests(project!.id, flowIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tests"] }),
  });

  if (!project) {
    return <div className="card">No project configured.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Flow Map</h1>
          <p className="mt-2 text-gray-400">Visualize inferred user flows and generate tests</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => generateMutation.mutate(undefined)}
          disabled={generateMutation.isPending || !graph?.flows?.length}
        >
          Generate All Tests
        </button>
      </div>

      <div className="card h-[400px]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Inferred Flows</h2>
        <div className="space-y-3">
          {(graph?.flows || []).map((flow) => (
            <div
              key={flow.id}
              className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] p-4"
            >
              <div>
                <div className="font-medium">{flow.name}</div>
                <div className="mt-1 flex gap-2 text-xs">
                  <span className="badge-neutral">{flow.steps.length} steps</span>
                  <span className="badge-neutral">confidence {(flow.confidence_score * 100).toFixed(0)}%</span>
                  <span className={flow.risk_level === "low" ? "badge-success" : "badge-warning"}>
                    {flow.risk_level} risk
                  </span>
                  {flow.destructive && <span className="badge-danger">destructive</span>}
                </div>
              </div>
              <button
                className="btn-secondary"
                onClick={() => generateMutation.mutate([flow.id])}
                disabled={generateMutation.isPending}
              >
                Generate Test
              </button>
            </div>
          ))}
          {!graph?.flows?.length && (
            <p className="text-gray-400">No flows inferred yet. Run a discovery crawl first.</p>
          )}
        </div>
      </div>
    </div>
  );
}
