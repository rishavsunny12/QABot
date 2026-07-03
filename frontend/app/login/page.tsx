"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";
import { API_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { devLogin, authConfig } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await devLogin(email, name || undefined);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--background))] p-6">
      <div className="card w-full max-w-md space-y-6">
        <div className="flex items-center gap-3">
          <Bot className="h-10 w-10 text-blue-400" />
          <div>
            <h1 className="text-2xl font-bold">Sign in to AutoQA</h1>
            <p className="text-sm text-gray-400">Enterprise testing workspace</p>
          </div>
        </div>

        {authConfig?.oidc_configured && (
          <a href={`${API_URL}/api/auth/login`} className="btn-primary block text-center">
            Continue with SSO
          </a>
        )}

        {authConfig?.dev_login_enabled && (
          <form onSubmit={handleDevLogin} className="space-y-4">
            {authConfig?.oidc_configured && (
              <div className="text-center text-xs text-gray-500">or use dev login</div>
            )}
            <div>
              <label className="text-sm text-gray-300">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-black/20 px-3 py-2"
              />
            </div>
            <div>
              <label className="text-sm text-gray-300">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-black/20 px-3 py-2"
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
