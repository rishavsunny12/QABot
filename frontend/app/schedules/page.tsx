"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Pause, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { useActiveProject } from "@/lib/hooks";

const INTERVAL_OPTIONS = [
  { label: "Every 15 minutes", value: 15 },
  { label: "Every hour", value: 60 },
  { label: "Every 6 hours", value: 360 },
  { label: "Every 24 hours", value: 1440 },
];

function formatWhen(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function SchedulesPage() {
  const { data: project } = useActiveProject();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [intervalMinutes, setIntervalMinutes] = useState(60);

  const { data: schedules } = useQuery({
    queryKey: ["schedules", project?.id],
    queryFn: () => api.listSchedules(project!.id),
    enabled: !!project?.id,
    refetchInterval: 30000,
  });

  const { data: tests } = useQuery({
    queryKey: ["tests", project?.id],
    queryFn: () => api.listTests(project!.id),
    enabled: !!project?.id,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createSchedule(project!.id, {
        name: name || "Daily regression",
        interval_minutes: intervalMinutes,
        enabled: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      setName("");
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => api.toggleSchedule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSchedule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });

  if (!project) {
    return <div className="card">Select a project to manage scheduled test runs.</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Scheduled Runs</h1>
        <p className="mt-2 text-gray-400">
          Automatically run tests for <span className="text-white">{project.name}</span> on a recurring interval.
        </p>
      </div>

      <form
        className="card grid gap-4 md:grid-cols-4 md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          createMutation.mutate();
        }}
      >
        <div className="md:col-span-2">
          <label className="mb-1 block text-sm text-gray-400">Schedule name</label>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nightly smoke tests"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-400">Interval</label>
          <select
            className="input"
            value={intervalMinutes}
            onChange={(e) => setIntervalMinutes(Number(e.target.value))}
          >
            {INTERVAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <button className="btn-primary" type="submit" disabled={createMutation.isPending}>
          Add Schedule
        </button>
      </form>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Active Schedules</h2>
        {!schedules?.length ? (
          <p className="text-gray-400">
            No schedules yet. Create one to run all tests in this project on a timer.
            {(tests?.length ?? 0) === 0 && " Generate tests first from the Flow Map."}
          </p>
        ) : (
          <div className="space-y-3">
            {schedules.map((schedule) => (
              <div
                key={schedule.id}
                className="flex flex-col gap-3 rounded-lg border border-[hsl(var(--border))] p-4 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <CalendarClock className="h-4 w-4 text-blue-400" />
                    <span className="font-medium">{schedule.name}</span>
                    <span className={schedule.enabled ? "badge-success" : "badge-neutral"}>
                      {schedule.enabled ? "Active" : "Paused"}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-1 text-xs text-gray-400 md:grid-cols-3">
                    <span>
                      Interval:{" "}
                      {INTERVAL_OPTIONS.find((o) => o.value === schedule.interval_minutes)?.label ??
                        `${schedule.interval_minutes} min`}
                    </span>
                    <span>Last run: {formatWhen(schedule.last_run_at)}</span>
                    <span>Next run: {formatWhen(schedule.next_run_at)}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn-secondary inline-flex items-center gap-1 text-xs"
                    onClick={() => toggleMutation.mutate(schedule.id)}
                    disabled={toggleMutation.isPending}
                  >
                    {schedule.enabled ? (
                      <>
                        <Pause className="h-3 w-3" /> Pause
                      </>
                    ) : (
                      <>
                        <Play className="h-3 w-3" /> Resume
                      </>
                    )}
                  </button>
                  <button
                    className="btn-secondary text-xs text-red-300"
                    onClick={() => {
                      if (confirm(`Delete schedule "${schedule.name}"?`)) {
                        deleteMutation.mutate(schedule.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card text-sm text-gray-400">
        <p>
          Celery Beat checks due schedules every minute. Scheduled runs appear in Run History with type{" "}
          <code className="text-gray-300">scheduled</code>.
        </p>
      </div>
    </div>
  );
}
