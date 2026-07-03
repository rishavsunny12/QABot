"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";

const STORAGE_KEY = "autoqa-active-project-id";

interface ProjectContextValue {
  projects: Project[];
  activeProject: Project | null;
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
  isLoading: boolean;
  refetchProjects: () => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const { activeTeamId } = useAuth();
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const { data: projects = [], isLoading, refetch } = useQuery({
    queryKey: ["projects", activeTeamId],
    queryFn: () => api.listProjects(activeTeamId),
  });

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setActiveProjectIdState(stored);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated || isLoading) return;

    if (!projects.length) {
      setActiveProjectIdState(null);
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    const stillExists = projects.some((p) => p.id === activeProjectId);
    if (!activeProjectId || !stillExists) {
      const nextId = projects[0].id;
      setActiveProjectIdState(nextId);
      localStorage.setItem(STORAGE_KEY, nextId);
    }
  }, [hydrated, isLoading, projects, activeProjectId]);

  const setActiveProjectId = useCallback((id: string | null) => {
    setActiveProjectIdState(id);
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const activeProject = useMemo(
    () => projects.find((p) => p.id === activeProjectId) ?? null,
    [projects, activeProjectId]
  );

  const value = useMemo(
    () => ({
      projects,
      activeProject,
      activeProjectId,
      setActiveProjectId,
      isLoading: isLoading || !hydrated,
      refetchProjects: () => {
        void refetch();
      },
    }),
    [projects, activeProject, activeProjectId, setActiveProjectId, isLoading, hydrated, refetch]
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProjectContext must be used within ProjectProvider");
  return ctx;
}
