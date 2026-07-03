"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function SetupPage() {
  const { data: project, isLoading } = useActiveProject();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    base_url: "https://demo.playwright.dev/todomvc",
    login_url: "",
    username: "",
    password: "",
    allowed_domains: "demo.playwright.dev",
    seed_urls: "https://demo.playwright.dev/todomvc",
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createProject({
        name: form.name || "Demo Project",
        base_url: form.base_url,
        login_url: form.login_url || null,
        username: form.username || null,
        password: form.password || null,
        allowed_domains: form.allowed_domains.split(",").map((d) => d.trim()).filter(Boolean),
        seed_urls: form.seed_urls.split(",").map((d) => d.trim()).filter(Boolean),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const crawlMutation = useMutation({
    mutationFn: () => api.startCrawl(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Project Setup</h1>
        <p className="mt-2 text-gray-400">
          Configure your target app, credentials, and domain allowlist.
        </p>
      </div>

      {project ? (
        <div className="card space-y-4">
          <h2 className="text-xl font-semibold">Active Project</h2>
          <div className="grid gap-2 text-sm">
            <div><span className="text-gray-400">Name:</span> {project.name}</div>
            <div><span className="text-gray-400">Base URL:</span> {project.base_url}</div>
            <div><span className="text-gray-400">Crawl status:</span> {project.crawl_status}</div>
            <div><span className="text-gray-400">Pages:</span> {project.crawl_pages_count}</div>
          </div>
          <button
            className="btn-primary"
            onClick={() => crawlMutation.mutate()}
            disabled={crawlMutation.isPending || project.crawl_status === "running"}
          >
            {crawlMutation.isPending ? "Starting..." : "Start Discovery Crawl"}
          </button>
        </div>
      ) : (
        <form
          className="card space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <div>
            <label className="mb-1 block text-sm text-gray-400">Project Name</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="My SaaS App"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Base URL</label>
            <input
              className="input"
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Login URL (optional)</label>
            <input
              className="input"
              value={form.login_url}
              onChange={(e) => setForm({ ...form, login_url: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm text-gray-400">Username</label>
              <input
                className="input"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">Password</label>
              <input
                className="input"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Allowed Domains (comma-separated)</label>
            <input
              className="input"
              value={form.allowed_domains}
              onChange={(e) => setForm({ ...form, allowed_domains: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Seed URLs (comma-separated)</label>
            <input
              className="input"
              value={form.seed_urls}
              onChange={(e) => setForm({ ...form, seed_urls: e.target.value })}
            />
          </div>
          <button className="btn-primary" type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create Project"}
          </button>
        </form>
      )}
    </div>
  );
}
