"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuthConfig, AuthUser } from "@/lib/types";

const TEAM_STORAGE_KEY = "autoqa-active-team-id";

interface AuthContextValue {
  user: AuthUser | null;
  authConfig: AuthConfig | null;
  activeTeamId: string | null;
  activeTeamRole: string | null;
  setActiveTeamId: (teamId: string | null) => void;
  isLoading: boolean;
  isAuthenticated: boolean;
  devLogin: (email: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  canAdmin: boolean;
  canEdit: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [activeTeamId, setActiveTeamIdState] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const { data: authConfig } = useQuery({
    queryKey: ["auth-config"],
    queryFn: () => api.getAuthConfig(),
  });

  const {
    data: user,
    isLoading: userLoading,
    refetch: refetchUser,
  } = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => api.getMe(),
    retry: false,
  });

  useEffect(() => {
    const stored = localStorage.getItem(TEAM_STORAGE_KEY);
    if (stored) setActiveTeamIdState(stored);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated || !user?.teams.length) return;
    const stillExists = user.teams.some((t) => t.team_id === activeTeamId);
    if (!activeTeamId || !stillExists) {
      const nextId = user.teams[0].team_id;
      setActiveTeamIdState(nextId);
      localStorage.setItem(TEAM_STORAGE_KEY, nextId);
    }
  }, [hydrated, user, activeTeamId]);

  const setActiveTeamId = useCallback((teamId: string | null) => {
    setActiveTeamIdState(teamId);
    if (teamId) localStorage.setItem(TEAM_STORAGE_KEY, teamId);
    else localStorage.removeItem(TEAM_STORAGE_KEY);
    queryClient.invalidateQueries({ queryKey: ["projects"] });
  }, [queryClient]);

  const devLogin = useCallback(
    async (email: string, name?: string) => {
      await api.devLogin(email, name);
      await refetchUser();
    },
    [refetchUser]
  );

  const logout = useCallback(async () => {
    await api.logout();
    queryClient.clear();
    setActiveTeamIdState(null);
    localStorage.removeItem(TEAM_STORAGE_KEY);
  }, [queryClient]);

  const activeTeamRole = useMemo(() => {
    if (!user || !activeTeamId) return null;
    return user.teams.find((t) => t.team_id === activeTeamId)?.role ?? null;
  }, [user, activeTeamId]);

  const roleRank = (role: string | null) => {
    const ranks: Record<string, number> = { viewer: 1, member: 2, admin: 3, owner: 4 };
    return role ? ranks[role] ?? 0 : 0;
  };

  const value = useMemo(
    () => ({
      user: user ?? null,
      authConfig: authConfig ?? null,
      activeTeamId,
      activeTeamRole,
      setActiveTeamId,
      isLoading: userLoading || !hydrated,
      isAuthenticated: !!user,
      devLogin,
      logout,
      canAdmin: roleRank(activeTeamRole) >= 3,
      canEdit: roleRank(activeTeamRole) >= 2,
    }),
    [
      user,
      authConfig,
      activeTeamId,
      activeTeamRole,
      setActiveTeamId,
      userLoading,
      hydrated,
      devLogin,
      logout,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
