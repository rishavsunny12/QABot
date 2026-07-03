"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

export default function SetupPage() {
  const { data: project, projects, isLoading, setActiveProjectId } = useActiveProject();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    base_url: "https://demo.playwright.dev/todomvc",
    login_url: "",
    username: "",
    password: "",
    allowed_domains: "demo.playwright.dev",
    seed_urls: "https://demo.playwright.dev/todomvc",
  });

  useEffect(() => {
    if (window.location.search.includes("new=1")) setShowForm(true);
  }, []);

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
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setActiveProjectId(created.id);
      setShowForm(false);
    },
  });

  const crawlMutation = useMutation({
    mutationFn: () => api.startCrawl(project!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Project Setup</h1>
          <p className="mt-2 text-gray-400">
            Configure target apps, credentials, and domain allowlists.
          </p>
        </div>
        <button className="btn-secondary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "New Project"}
        </button>
      </div>

      {projects.length > 0 && (
        <div className="card">
          <h2 className="mb-3 text-sm font-medium text-gray-400">Your Projects</h2>
          <div className="space-y-2">
            {projects.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setActiveProjectId(p.id)}
                className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  p.id === project?.id
                    ? "border-blue-500/50 bg-blue-600/10"
                    : "border-[hsl(var(--border))] hover:bg-white/5"
                }`}
              >
                <span>
                  <span className="font-medium">{p.name}</span>
                  <span className="ml-2 text-xs text-gray-400">{p.base_url}</span>
                </span>
                <span className="badge-neutral capitalize">{p.crawl_status}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {showForm && (
        <form
          className="card space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <h2 className="text-xl font-semibold">Create New Project</h2>
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

      {project && !showForm && (
        <div className="card space-y-4">
          <h2 className="text-xl font-semibold">Active Project: {project.name}</h2>
          <div className="grid gap-2 text-sm">
            <div><span className="text-gray-400">Base URL:</span> {project.base_url}</div>
            <div><span className="text-gray-400">Crawl status:</span> {project.crawl_status}</div>
            <div><span className="text-gray-400">Pages:</span> {project.crawl_pages_count}</div>
            <div><span className="text-gray-400">Elements:</span> {project.crawl_elements_count}</div>
          </div>
          <button
            className="btn-primary"
            onClick={() => crawlMutation.mutate()}
            disabled={crawlMutation.isPending || project.crawl_status === "running"}
          >
            {crawlMutation.isPending ? "Starting..." : "Start Discovery Crawl"}
          </button>
        </div>
      )}

      {!project && !showForm && (
        <div className="card text-gray-400">
          No project selected. Create a new project to get started.
        </div>
      )}
    </div>
  );
}
