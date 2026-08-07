"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchObservations } from "@/lib/api";
import type { ObservationSummary } from "@/types/observation";

const POLL_INTERVAL_MS = 10_000;

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  pending: { bg: "bg-zinc-700", text: "text-zinc-200", label: "Pending" },
  downloading: { bg: "bg-blue-800", text: "text-blue-200", label: "Downloading" },
  processing: { bg: "bg-yellow-700", text: "text-yellow-100", label: "Processing" },
  completed: { bg: "bg-green-700", text: "text-green-100", label: "Completed" },
  failed: { bg: "bg-red-700", text: "text-red-100", label: "Failed" },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? {
    bg: "bg-zinc-700",
    text: "text-zinc-200",
    label: status,
  };
  return (
    <span
      className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

interface DashboardClientProps {
  initialObservations: ObservationSummary[];
}

export function DashboardClient({ initialObservations }: DashboardClientProps) {
  const [observations, setObservations] = useState<ObservationSummary[]>(initialObservations);

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const fresh = await fetchObservations();
        setObservations(fresh);
      } catch {
        // Keep showing stale data; don't crash on transient errors.
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  if (observations.length === 0) {
    return (
      <main className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold mb-6">Pipeline Dashboard</h1>
        <p className="text-zinc-500 text-sm">No observations ingested yet.</p>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Pipeline Dashboard</h1>
      <div className="space-y-4">
        {observations.map((obs) => (
          <div key={obs.observation_uuid} className="bg-zinc-900 rounded p-4 space-y-3">
            {/* Header row: observation ID + status badge */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-sm break-all">{obs.archive_observation_id}</p>
                <p className="text-zinc-500 text-xs mt-0.5">
                  Ingested {new Date(obs.ingested_at).toLocaleString()}
                </p>
              </div>
              <StatusBadge status={obs.pipeline_status} />
            </div>

            {/* Object counts */}
            <div className="flex flex-wrap gap-6 text-sm">
              <span>
                <span className="text-zinc-400">Objects </span>
                <span className="font-mono tabular-nums">{obs.object_count}</span>
              </span>
              <span>
                <span className="text-zinc-400">Classified </span>
                <span className="font-mono tabular-nums">{obs.classified_count}</span>
              </span>
              <span>
                <span className="text-zinc-400">Anomalies </span>
                <span className="font-mono tabular-nums">{obs.anomaly_count}</span>
              </span>
            </div>

            {/* Processing step timeline */}
            {obs.steps.length > 0 && (
              <ol className="text-xs space-y-1 border-l-2 border-zinc-700 pl-3 ml-1">
                {obs.steps.map((step) => (
                  <li key={step.step_name} className="flex justify-between gap-4">
                    <span className="capitalize text-zinc-300">
                      {step.step_name.replace(/_/g, " ")}
                    </span>
                    <span className="text-zinc-500 tabular-nums shrink-0">
                      {step.step_completed_at
                        ? new Date(step.step_completed_at).toLocaleTimeString()
                        : step.step_started_at
                          ? new Date(step.step_started_at).toLocaleTimeString()
                          : "—"}
                    </span>
                  </li>
                ))}
              </ol>
            )}

            {/* Sky viewer link */}
            <div>
              <Link
                href={`/viewer/${obs.observation_uuid}`}
                className="text-blue-400 hover:underline text-sm"
              >
                Open in sky viewer →
              </Link>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
