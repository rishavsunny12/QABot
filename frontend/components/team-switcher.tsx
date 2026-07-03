"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function TeamSwitcher() {
  const { user, activeTeamId, setActiveTeamId } = useAuth();
  const queryClient = useQueryClient();

  const createTeam = useMutation({
    mutationFn: (name: string) => api.createTeam(name),
    onSuccess: (team) => {
      queryClient.invalidateQueries({ queryKey: ["auth-me"] });
      setActiveTeamId(team.id);
    },
  });

  if (!user?.teams.length) return null;

  return (
    <div className="mb-4 px-2">
      <label className="mb-1 flex items-center gap-2 text-xs text-gray-400">
        <Users className="h-3 w-3" />
        Team
      </label>
      <select
        className="w-full rounded-lg border border-[hsl(var(--border))] bg-black/20 px-3 py-2 text-sm"
        value={activeTeamId || ""}
        onChange={(e) => setActiveTeamId(e.target.value || null)}
      >
        {user.teams.map((team) => (
          <option key={team.team_id} value={team.team_id}>
            {team.team_name} ({team.role})
          </option>
        ))}
      </select>
      <button
        className="mt-2 w-full text-xs text-blue-400 hover:underline"
        onClick={() => {
          const name = prompt("New team name");
          if (name) createTeam.mutate(name);
        }}
      >
        + Create team
      </button>
    </div>
  );
}
