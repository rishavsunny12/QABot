"use client";

import { ChevronDown, FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useActiveProject } from "@/lib/hooks";

export function ProjectSwitcher() {
  const { data: project, projects, isLoading, setActiveProjectId } = useActiveProject();
  const [open, setOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="mb-4 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs text-gray-400">
        Loading projects...
      </div>
    );
  }

  return (
    <div className="relative mb-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-lg border border-[hsl(var(--border))] bg-black/20 px-3 py-2 text-left text-sm hover:bg-white/5"
      >
        <span className="flex min-w-0 items-center gap-2">
          <FolderKanban className="h-4 w-4 shrink-0 text-blue-400" />
          <span className="truncate">{project?.name ?? "No project selected"}</span>
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute left-0 right-0 z-20 mt-1 max-h-64 overflow-auto rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-1 shadow-xl">
          {projects.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setActiveProjectId(p.id);
                setOpen(false);
              }}
              className={`flex w-full flex-col px-3 py-2 text-left text-sm hover:bg-white/5 ${
                p.id === project?.id ? "bg-blue-600/10 text-blue-300" : ""
              }`}
            >
              <span className="truncate font-medium">{p.name}</span>
              <span className="truncate text-xs text-gray-400">{p.base_url}</span>
            </button>
          ))}
          <Link
            href="/setup?new=1"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 border-t border-[hsl(var(--border))] px-3 py-2 text-sm text-blue-300 hover:bg-white/5"
          >
            <Plus className="h-4 w-4" />
            New project
          </Link>
        </div>
      )}
    </div>
  );
}
