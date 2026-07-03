"use client";

import { useProjectContext } from "@/lib/project-context";

export function useActiveProject() {
  const { activeProject, activeProjectId, isLoading, projects, setActiveProjectId, refetchProjects } =
    useProjectContext();

  return {
    data: activeProject,
    isLoading,
    projects,
    activeProjectId,
    setActiveProjectId,
    refetchProjects,
  };
}

export function useProjects() {
  const { projects, isLoading, refetchProjects } = useProjectContext();
  return { projects, isLoading, refetchProjects };
}
