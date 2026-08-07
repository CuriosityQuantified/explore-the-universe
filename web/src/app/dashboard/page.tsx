import { DashboardClient } from "./DashboardClient";
import { fetchObservations } from "@/lib/api";
import type { ObservationSummary } from "@/types/observation";

export const metadata = {
  title: "Pipeline Dashboard — Explore the Universe",
};

export default async function DashboardPage() {
  let initialObservations: ObservationSummary[] = [];
  try {
    initialObservations = await fetchObservations();
  } catch {
    // Render with empty list; the client component will retry on next poll.
  }

  return <DashboardClient initialObservations={initialObservations} />;
}
