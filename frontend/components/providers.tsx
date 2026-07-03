"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { ProjectProvider } from "@/lib/project-context";

function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading, authConfig } = useAuth();

  useEffect(() => {
    if (isLoading || pathname === "/login") return;
    if (authConfig?.mode !== "disabled" && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, authConfig, pathname, router]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-400">
        Loading workspace...
      </div>
    );
  }

  if (authConfig?.mode !== "disabled" && !isAuthenticated) {
    return null;
  }

  return (
    <ProjectProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto p-8">{children}</main>
      </div>
    </ProjectProvider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <AuthGate>{children}</AuthGate>
      </AuthProvider>
    </QueryClientProvider>
  );
}
