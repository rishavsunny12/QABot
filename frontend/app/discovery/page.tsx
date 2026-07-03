"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function DiscoveryPage() {
  const { data: project } = useActiveProject();

  const { data: status } = useQuery({
    queryKey: ["crawl-status", project?.id],
    queryFn: () => api.crawlStatus(project!.id),
    enabled: !!project?.id,
    refetchInterval: (query) =>
      query.state.data?.status === "running" || query.state.data?.status === "queued" ? 3000 : false,
  });

  const { data: pages } = useQuery({
    queryKey: ["pages", project?.id],
    queryFn: () => api.listPages(project!.id),
    enabled: !!project?.id,
    refetchInterval: status?.status === "running" ? 5000 : false,
  });

  const { data: flows } = useQuery({
    queryKey: ["flows", project?.id],
    queryFn: () => api.listFlows(project!.id),
    enabled: !!project?.id,
  });

  if (!project) {
    return (
      <div className="card">
        <p>No project configured. Go to Project Setup to create one.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Discovery Overview</h1>
        <p className="mt-2 text-gray-400">Crawl status and discovered pages for {project.name}</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="text-sm text-gray-400">Crawl Status</div>
          <div className="mt-2 text-2xl font-semibold capitalize">{status?.status || project.crawl_status}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400">Pages</div>
          <div className="mt-2 text-2xl font-semibold">{status?.pages_count ?? project.crawl_pages_count}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400">Elements</div>
          <div className="mt-2 text-2xl font-semibold">{status?.elements_count ?? project.crawl_elements_count}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400">Inferred Flows</div>
          <div className="mt-2 text-2xl font-semibold">{flows?.length ?? 0}</div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Latest Screenshots</h2>
        <div className="grid grid-cols-3 gap-4">
          {(pages || []).slice(0, 6).map((page) => (
            <div key={page.id} className="overflow-hidden rounded-lg border border-[hsl(var(--border))]">
              <img
                src={api.screenshotUrl(project.id, page.id)}
                alt={page.title || page.url}
                className="h-40 w-full object-cover object-top bg-black/40"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
              <div className="p-2 text-xs">
                <div className="truncate font-medium">{page.title || "Untitled"}</div>
                <div className="truncate text-gray-400">{page.url}</div>
                <div className="text-gray-500">{page.elements.length} elements</div>
              </div>
            </div>
          ))}
          {!pages?.length && <p className="text-gray-400">No pages discovered yet. Start a crawl from Project Setup.</p>}
        </div>
      </div>
    </div>
  );
}
