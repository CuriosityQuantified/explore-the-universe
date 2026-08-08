"use client";

/**
 * QueryBuilder — collapsible structured filter panel for /search.
 *
 * Fetches available object types from GET /api/objects/types and
 * available observations from GET /api/observations. When the user
 * clicks Search it POSTs to /api/objects/search via the searchByFilters
 * API helper and passes results up via onResults callback.
 */

import { useEffect, useRef, useState } from "react";
import { fetchObjectTypes, fetchObservations, searchByFilters } from "@/lib/api";
import type { ObjectSearchItem, StructuredSearchFilters } from "@/types/search";
import type { ObservationSummary } from "@/types/observation";

interface QueryBuilderProps {
  /** Called with the matching objects and the total count after a search. */
  onResults: (results: ObjectSearchItem[], totalCount: number) => void;
  /** Called when a search is initiated (for loading state). */
  onLoading?: (loading: boolean) => void;
  /** Called when an error occurs. */
  onError?: (error: string | null) => void;
  /** Current page offset driven by the parent (for pagination). When this changes after a search, re-fires the search. */
  offset?: number;
  /** Called when the user clicks Search so the parent can reset its offset to 0. */
  onOffsetReset?: () => void;
}

const PAGE_SIZE = 24;

export default function QueryBuilder({ onResults, onLoading, onError, offset = 0, onOffsetReset }: QueryBuilderProps) {
  const [open, setOpen] = useState(false);
  const hasSearched = useRef(false);
  const lastFiltersRef = useRef<StructuredSearchFilters | null>(null);

  // Filter state
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [magnitudeMin, setMagnitudeMin] = useState("");
  const [magnitudeMax, setMagnitudeMax] = useState("");
  const [redshiftMin, setRedshiftMin] = useState("");
  const [redshiftMax, setRedshiftMax] = useState("");
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [observationUuid, setObservationUuid] = useState("");
  const [sortBy, setSortBy] = useState<"magnitude" | "type" | "angular_separation">("magnitude");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Data for dropdowns
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [observations, setObservations] = useState<ObservationSummary[]>([]);

  useEffect(() => {
    fetchObjectTypes().then(setAvailableTypes).catch(() => {});
    fetchObservations().then(setObservations).catch(() => {});
  }, []);

  // Re-fire the last search when the parent pages (offset changes after first search).
  useEffect(() => {
    if (!hasSearched.current || lastFiltersRef.current === null) return;
    const f = { ...lastFiltersRef.current, offset };
    onLoading?.(true);
    onError?.(null);
    searchByFilters(f)
      .then((res) => { onResults(res.results, res.total_count); })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Search failed";
        onError?.(msg);
        onResults([], 0);
      })
      .finally(() => onLoading?.(false));
    // offset is the only external trigger; other deps are stable callbacks
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  function toggleType(t: string) {
    setSelectedTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  }

  async function handleSearch(pageOffset = 0) {
    onLoading?.(true);
    onError?.(null);

    const filters: StructuredSearchFilters = {
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: PAGE_SIZE,
      offset: pageOffset,
    };

    if (selectedTypes.length > 0) filters.type = selectedTypes;
    if (magnitudeMin !== "") filters.magnitude_min = parseFloat(magnitudeMin);
    if (magnitudeMax !== "") filters.magnitude_max = parseFloat(magnitudeMax);
    if (redshiftMin !== "") filters.redshift_min = parseFloat(redshiftMin);
    if (redshiftMax !== "") filters.redshift_max = parseFloat(redshiftMax);
    if (anomalyOnly) filters.is_anomaly = true;
    if (observationUuid !== "") filters.observation_uuid = observationUuid;

    // Store filters so pagination can re-fire with a new offset
    lastFiltersRef.current = filters;
    hasSearched.current = true;

    // When user clicks Search, notify parent to reset offset to 0
    onOffsetReset?.();

    try {
      const res = await searchByFilters(filters);
      onResults(res.results, res.total_count);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      onError?.(msg);
      onResults([], 0);
    } finally {
      onLoading?.(false);
    }
  }

  return (
    <div className="mb-6 rounded border border-zinc-700 bg-zinc-800">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-zinc-200 hover:bg-zinc-700/50 transition-colors"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <span>Filters</span>
          {(selectedTypes.length > 0 || magnitudeMin || magnitudeMax || redshiftMin || redshiftMax || anomalyOnly || observationUuid) && (
            <span className="inline-block rounded-full bg-indigo-600 px-2 py-0.5 text-xs text-white">
              active
            </span>
          )}
        </span>
        <span className="text-zinc-400">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-700 px-4 py-4 space-y-5">
          {/* Object type checkboxes */}
          {availableTypes.length > 0 && (
            <fieldset>
              <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Object Type
              </legend>
              <div className="flex flex-wrap gap-2">
                {availableTypes.map((t) => (
                  <label
                    key={t}
                    className={`flex cursor-pointer items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors ${
                      selectedTypes.includes(t)
                        ? "bg-indigo-700 text-white"
                        : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={selectedTypes.includes(t)}
                      onChange={() => toggleType(t)}
                    />
                    {t}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {/* Magnitude range */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Magnitude
            </p>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.1"
                placeholder="Min"
                value={magnitudeMin}
                onChange={(e) => setMagnitudeMin(e.target.value)}
                className="w-24 rounded bg-zinc-900 border border-zinc-600 px-2 py-1 text-sm text-zinc-200 placeholder-zinc-500 focus:border-indigo-400 focus:outline-none"
              />
              <span className="text-zinc-500 text-sm">–</span>
              <input
                type="number"
                step="0.1"
                placeholder="Max"
                value={magnitudeMax}
                onChange={(e) => setMagnitudeMax(e.target.value)}
                className="w-24 rounded bg-zinc-900 border border-zinc-600 px-2 py-1 text-sm text-zinc-200 placeholder-zinc-500 focus:border-indigo-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Redshift range */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Redshift
            </p>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.001"
                min="0"
                placeholder="Min"
                value={redshiftMin}
                onChange={(e) => setRedshiftMin(e.target.value)}
                className="w-24 rounded bg-zinc-900 border border-zinc-600 px-2 py-1 text-sm text-zinc-200 placeholder-zinc-500 focus:border-indigo-400 focus:outline-none"
              />
              <span className="text-zinc-500 text-sm">–</span>
              <input
                type="number"
                step="0.001"
                min="0"
                placeholder="Max"
                value={redshiftMax}
                onChange={(e) => setRedshiftMax(e.target.value)}
                className="w-24 rounded bg-zinc-900 border border-zinc-600 px-2 py-1 text-sm text-zinc-200 placeholder-zinc-500 focus:border-indigo-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Anomaly toggle */}
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={anomalyOnly}
              onChange={(e) => setAnomalyOnly(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-500 bg-zinc-700 accent-indigo-500"
            />
            <span className="text-sm text-zinc-300">Anomalies only</span>
          </label>

          {/* Observation selector */}
          {observations.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Observation
              </p>
              <select
                value={observationUuid}
                onChange={(e) => setObservationUuid(e.target.value)}
                className="w-full rounded bg-zinc-900 border border-zinc-600 px-2 py-1.5 text-sm text-zinc-200 focus:border-indigo-400 focus:outline-none"
              >
                <option value="">All observations</option>
                {observations.map((obs) => (
                  <option key={obs.observation_uuid} value={obs.observation_uuid}>
                    {obs.archive_observation_id || obs.observation_uuid}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sort controls */}
          <div className="flex flex-wrap gap-3">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Sort By
              </p>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="rounded bg-zinc-900 border border-zinc-600 px-2 py-1.5 text-sm text-zinc-200 focus:border-indigo-400 focus:outline-none"
              >
                <option value="magnitude">Magnitude</option>
                <option value="type">Type</option>
                <option value="angular_separation">Angular Separation</option>
              </select>
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Order
              </p>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}
                className="rounded bg-zinc-900 border border-zinc-600 px-2 py-1.5 text-sm text-zinc-200 focus:border-indigo-400 focus:outline-none"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>
          </div>

          {/* Search button */}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={() => handleSearch(0)}
              className="rounded bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 active:bg-indigo-700 transition-colors"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedTypes([]);
                setMagnitudeMin("");
                setMagnitudeMax("");
                setRedshiftMin("");
                setRedshiftMax("");
                setAnomalyOnly(false);
                setObservationUuid("");
                setSortBy("magnitude");
                setSortOrder("asc");
              }}
              className="text-sm text-zinc-400 hover:text-zinc-200"
            >
              Reset
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
