"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useActiveProject() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
    select: (projects) => projects[0] ?? null,
  });
}
