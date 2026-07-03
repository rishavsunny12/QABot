"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const METRIC_LABELS: Record<string, string> = {
  test_runs: "Test runs",
  crawl_pages: "Crawl pages",
  ai_calls: "AI analysis calls",
  visual_comparisons: "Visual comparisons",
  projects: "Active projects",
};

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const unlimited = limit === null || limit < 0;
  const pct = unlimited ? 0 : Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-300">{label}</span>
        <span className="text-gray-400">
          {used}
          {unlimited ? " / unlimited" : ` / ${limit}`}
        </span>
      </div>
      {!unlimited && (
        <div className="h-2 overflow-hidden rounded-full bg-gray-800">
          <div
            className={`h-full rounded-full ${pct >= 90 ? "bg-red-500" : "bg-blue-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default function BillingPage() {
  const { activeTeamId, canAdmin } = useAuth();
  const queryClient = useQueryClient();

  const { data: billing, isLoading } = useQuery({
    queryKey: ["team-billing", activeTeamId],
    queryFn: () => api.getTeamBilling(activeTeamId!),
    enabled: !!activeTeamId,
  });

  const { data: plans } = useQuery({
    queryKey: ["billing-plans"],
    queryFn: () => api.listBillingPlans(),
  });

  const changePlan = useMutation({
    mutationFn: (slug: string) => api.changeTeamPlan(activeTeamId!, slug),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team-billing", activeTeamId] }),
  });

  if (!activeTeamId) {
    return <div className="card">Select a team to view billing.</div>;
  }

  if (isLoading || !billing) {
    return <div className="card text-gray-400">Loading billing data...</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-3xl font-bold">
          <CreditCard className="h-8 w-8 text-blue-400" />
          Billing & Usage
        </h1>
        <p className="mt-2 text-gray-400">
          Current plan: <span className="text-white">{billing.plan.name}</span>
          {billing.plan.price_cents > 0 && (
            <span> — ${(billing.plan.price_cents / 100).toFixed(0)}/mo</span>
          )}
        </p>
        <p className="text-xs text-gray-500">
          Period: {new Date(billing.period_start).toLocaleDateString()} –{" "}
          {new Date(billing.period_end).toLocaleDateString()}
        </p>
      </div>

      <div className="card space-y-4">
        <h2 className="text-xl font-semibold">Usage this period</h2>
        {Object.entries(billing.usage).map(([metric, values]) => (
          <UsageBar
            key={metric}
            label={METRIC_LABELS[metric] || metric}
            used={values.used}
            limit={values.limit}
          />
        ))}
      </div>

      {canAdmin && (
        <div className="card space-y-4">
          <h2 className="text-xl font-semibold">Plans</h2>
          <p className="text-sm text-gray-400">
            Upgrade instantly (payment integration coming soon — no charge in MVP).
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {(plans || []).map((plan) => (
              <div
                key={plan.slug}
                className={`rounded-lg border p-4 ${
                  billing.plan.slug === plan.slug
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-[hsl(var(--border))]"
                }`}
              >
                <div className="font-semibold">{plan.name}</div>
                <div className="mt-1 text-2xl font-bold">
                  {plan.price_cents === 0 ? "Free" : `$${plan.price_cents / 100}`}
                </div>
                <ul className="mt-3 space-y-1 text-xs text-gray-400">
                  <li>{plan.limits.test_runs ?? "∞"} test runs</li>
                  <li>{plan.limits.crawl_pages ?? "∞"} crawl pages</li>
                  <li>{plan.limits.projects ?? "∞"} projects</li>
                </ul>
                <button
                  className="btn-secondary mt-4 w-full text-xs"
                  disabled={billing.plan.slug === plan.slug || changePlan.isPending}
                  onClick={() => changePlan.mutate(plan.slug)}
                >
                  {billing.plan.slug === plan.slug ? "Current plan" : "Select plan"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
