"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, FolderKanban, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function WorkspacePage() {
  const { projects, isLoading, setActiveProjectId, activeProjectId } = useActiveProject();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (isLoading) return <div>Loading workspace...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Workspace</h1>
          <p className="mt-2 text-gray-400">
            Manage all your AutoQA projects in one place.
          </p>
        </div>
        <Link href="/setup?new=1" className="btn-primary inline-flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      {!projects.length ? (
        <div className="card text-center">
          <FolderKanban className="mx-auto mb-4 h-12 w-12 text-gray-500" />
          <h2 className="text-xl font-semibold">No projects yet</h2>
          <p className="mt-2 text-gray-400">Create your first project to start discovering and testing apps.</p>
          <Link href="/setup" className="btn-primary mt-6 inline-block">
            Create Project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className={`card flex flex-col ${
                project.id === activeProjectId ? "ring-1 ring-blue-500/50" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold">{project.name}</h2>
                  <p className="mt-1 truncate text-sm text-gray-400">{project.base_url}</p>
                </div>
                {project.id === activeProjectId && (
                  <span className="badge-success shrink-0">Active</span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-lg bg-black/20 p-2">
                  <div className="text-gray-400">Status</div>
                  <div className="mt-1 capitalize">{project.crawl_status}</div>
                </div>
                <div className="rounded-lg bg-black/20 p-2">
                  <div className="text-gray-400">Pages</div>
                  <div className="mt-1">{project.crawl_pages_count}</div>
                </div>
                <div className="rounded-lg bg-black/20 p-2">
                  <div className="text-gray-400">Elements</div>
                  <div className="mt-1">{project.crawl_elements_count}</div>
                </div>
              </div>

              <div className="mt-auto flex gap-2 pt-4">
                <button
                  className="btn-primary flex-1 text-xs"
                  onClick={() => setActiveProjectId(project.id)}
                >
                  {project.id === activeProjectId ? "Selected" : "Select"}
                </button>
                <Link href="/discovery" className="btn-secondary text-xs" onClick={() => setActiveProjectId(project.id)}>
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  className="btn-secondary text-xs text-red-300"
                  onClick={() => {
                    if (confirm(`Delete project "${project.name}"?`)) {
                      deleteMutation.mutate(project.id);
                    }
                  }}
                  disabled={deleteMutation.isPending}
                  aria-label="Delete project"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
