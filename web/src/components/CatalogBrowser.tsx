"use client";

import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";
import { fetchCatalogObjects, fetchObjectTypes } from "@/lib/api";
import type { CatalogFilters, CatalogPage, CatalogSort } from "@/types/catalog";

const controlClass = "w-full min-w-0 rounded border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-400";
const buttonClass = "rounded border border-zinc-600 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-indigo-400 disabled:cursor-not-allowed disabled:opacity-40";
const sortLabels: Record<CatalogSort, string> = {
  name: "Name", type: "Object type", magnitude: "Magnitude", redshift: "Redshift",
  ra: "Right ascension", dec: "Declination",
};

interface BrowserState {
  q: string;
  type: string;
  image: "all" | "ready" | "queued";
  hemisphere: "all" | "north" | "south";
  magnitudeMin: string;
  magnitudeMax: string;
  sort: CatalogSort;
  order: "asc" | "desc";
  limit: number;
  offset: number;
}

const initialState: BrowserState = {
  q: "", type: "", image: "all", hemisphere: "all", magnitudeMin: "", magnitudeMax: "",
  sort: "name", order: "asc", limit: 25, offset: 0,
};

function readableType(value: string | null): string {
  return value ? value.replaceAll("_", " ") : "Unclassified";
}

export function CatalogBrowser() {
  const id = useId();
  const [filters, setFilters] = useState<BrowserState>(initialState);
  const [response, setResponse] = useState<{ key: string; page: CatalogPage } | null>(null);
  const [error, setError] = useState<{ key: string; message: string } | null>(null);
  const [retry, setRetry] = useState(0);
  const [types, setTypes] = useState<string[]>([]);
  const [typesError, setTypesError] = useState(false);
  const [typesRetry, setTypesRetry] = useState(0);
  const requestKey = JSON.stringify({ filters, retry });
  const invalidMagnitude = (filters.magnitudeMin !== "" && !Number.isFinite(Number(filters.magnitudeMin)))
    || (filters.magnitudeMax !== "" && !Number.isFinite(Number(filters.magnitudeMax)))
    || (filters.magnitudeMin !== "" && filters.magnitudeMax !== ""
      && Number(filters.magnitudeMin) > Number(filters.magnitudeMax));
  const page = response?.key === requestKey ? response.page : null;
  const message = error?.key === requestKey ? error.message : null;
  const loading = !invalidMagnitude && !page && !message;

  useEffect(() => {
    const controller = new AbortController();
    fetchObjectTypes(controller.signal)
      .then((values) => {
        if (controller.signal.aborted) return;
        setTypes(values);
        setTypesError(false);
      })
      .catch(() => { if (!controller.signal.aborted) setTypesError(true); });
    return () => controller.abort();
  }, [typesRetry]);

  useEffect(() => {
    if (invalidMagnitude) return;
    const controller = new AbortController();
    const params: CatalogFilters = {
      q: filters.q.trim() || undefined,
      type: filters.type || undefined,
      has_image: filters.image === "all" ? undefined : filters.image === "ready",
      hemisphere: filters.hemisphere === "all" ? undefined : filters.hemisphere,
      magnitude_min: filters.magnitudeMin === "" ? undefined : Number(filters.magnitudeMin),
      magnitude_max: filters.magnitudeMax === "" ? undefined : Number(filters.magnitudeMax),
      sort_by: filters.sort, sort_order: filters.order, limit: filters.limit, offset: filters.offset,
    };
    // Debounce edits and abort obsolete requests so late responses cannot replace current results.
    const timer = setTimeout(() => {
      fetchCatalogObjects(params, controller.signal)
        .then((result) => {
          if (controller.signal.aborted) return;
          setResponse({ key: requestKey, page: result });
          setError(null);
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          setError({ key: requestKey, message: err instanceof Error ? err.message : "Could not load the catalog." });
        });
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [filters, requestKey, invalidMagnitude]);

  function update(patch: Partial<BrowserState>) {
    setFilters((current) => ({ ...current, ...patch, offset: 0 }));
  }

  function sortBy(sort: CatalogSort) {
    update({ sort, order: filters.sort === sort && filters.order === "asc" ? "desc" : "asc" });
  }

  function reset() {
    setFilters(initialState);
    setRetry((value) => value + 1);
  }

  const totalPages = page ? Math.max(1, Math.ceil(page.total_count / filters.limit)) : 1;
  const currentPage = Math.floor(filters.offset / filters.limit) + 1;

  function goToPage(number: number) {
    setFilters((current) => ({ ...current, offset: (Math.max(1, Math.min(totalPages, number)) - 1) * current.limit }));
  }

  function jumpToPage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = Number(new FormData(event.currentTarget).get("page"));
    if (Number.isInteger(value)) goToPage(value);
  }

  function column(label: string, sort: CatalogSort, className = "") {
    const active = filters.sort === sort;
    return (
      <th scope="col" className={`px-3 py-3 font-medium ${className}`}
        aria-sort={active ? (filters.order === "asc" ? "ascending" : "descending") : "none"}>
        <button type="button" onClick={() => sortBy(sort)}
          className="text-left hover:text-indigo-300 focus-visible:outline-2 focus-visible:outline-indigo-400"
          aria-label={`Sort by ${sortLabels[sort]} ${active && filters.order === "asc" ? "descending" : "ascending"}`}>
          {label}<span aria-hidden="true">{active ? (filters.order === "asc" ? " ↑" : " ↓") : " ↕"}</span>
        </button>
      </th>
    );
  }

  return (
    <section aria-labelledby={`${id}-title`} className="text-left">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id={`${id}-title`} className="text-lg font-medium text-zinc-100">Browse the catalog</h2>
          <p className="mt-1 text-sm text-zinc-400">Explore every available object. Select a name to open its details.</p>
        </div>
        <button type="button" onClick={reset} className={buttonClass}>Reset filters</button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <label className="col-span-2 flex flex-col gap-1.5 text-xs text-zinc-300">
          Name or alias
          <input type="search" value={filters.q} onChange={(event) => update({ q: event.target.value })}
            placeholder="Try M31, NGC 253, or Andromeda" maxLength={120} className={controlClass} />
        </label>
        <label className="flex flex-col gap-1.5 text-xs text-zinc-300">
          Object type
          <select value={filters.type} onChange={(event) => update({ type: event.target.value })} className={controlClass}>
            <option value="">All types</option>
            {types.map((type) => <option key={type} value={type}>{readableType(type)}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs text-zinc-300">
          Imagery
          <select value={filters.image} onChange={(event) => update({ image: event.target.value as BrowserState["image"] })} className={controlClass}>
            <option value="all">All objects</option><option value="ready">Image ready</option><option value="queued">Image queued</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs text-zinc-300">
          Sky hemisphere
          <select value={filters.hemisphere} onChange={(event) => update({ hemisphere: event.target.value as BrowserState["hemisphere"] })} className={controlClass}>
            <option value="all">Both hemispheres</option><option value="north">Northern sky</option><option value="south">Southern sky</option>
          </select>
        </label>
        <fieldset className="min-w-0">
          <legend className="mb-1.5 text-xs text-zinc-300">Magnitude range</legend>
          <div className="flex items-center gap-2">
            <input type="number" step="any" aria-label="Minimum magnitude" placeholder="Min" value={filters.magnitudeMin}
              onChange={(event) => update({ magnitudeMin: event.target.value })} className={controlClass}
              aria-invalid={invalidMagnitude} aria-describedby={`${id}-magnitude-help`} />
            <span className="text-zinc-500" aria-hidden="true">–</span>
            <input type="number" step="any" aria-label="Maximum magnitude" placeholder="Max" value={filters.magnitudeMax}
              onChange={(event) => update({ magnitudeMax: event.target.value })} className={controlClass}
              aria-invalid={invalidMagnitude} aria-describedby={`${id}-magnitude-help`} />
          </div>
        </fieldset>
        <label className="flex flex-col gap-1.5 text-xs text-zinc-300">
          Sort by
          <select value={filters.sort} onChange={(event) => update({ sort: event.target.value as CatalogSort })} className={controlClass}>
            {Object.entries(sortLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs text-zinc-300">
          Sort direction
          <select value={filters.order} onChange={(event) => update({ order: event.target.value as BrowserState["order"] })} className={controlClass}>
            <option value="asc">Ascending</option><option value="desc">Descending</option>
          </select>
        </label>
      </div>
      <p id={`${id}-magnitude-help`} className={`mt-2 text-xs ${invalidMagnitude ? "text-red-300" : "text-zinc-400"}`}>
        {invalidMagnitude ? "Enter a valid magnitude range with the minimum no greater than the maximum." : "Lower magnitudes mean brighter objects. A range excludes objects with unknown magnitude."}
      </p>
      {typesError && <p role="alert" className="mt-2 text-sm text-amber-300">
        Object types could not be loaded. <button type="button" className="underline" onClick={() => setTypesRetry((value) => value + 1)}>Retry types</button>
      </p>}

      <div className="my-4 flex flex-wrap items-center justify-between gap-3">
        <p role="status" aria-live="polite" className="text-sm text-zinc-300">
          {invalidMagnitude ? "Adjust the magnitude range to continue." : loading ? "Loading objects…" : page
            ? `${page.total_count.toLocaleString()} object${page.total_count === 1 ? "" : "s"}${page.total_count ? ` · Showing ${(page.offset + 1).toLocaleString()}–${(page.offset + page.results.length).toLocaleString()}` : ""}`
            : "Catalog unavailable"}
        </p>
        <label className="flex items-center gap-2 text-xs text-zinc-300">
          Per page
          <select value={filters.limit} onChange={(event) => update({ limit: Number(event.target.value) })} className={`${controlClass} w-auto`}>
            {[25, 50, 100].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
      </div>

      <div aria-busy={loading} className="min-h-40 rounded border border-zinc-700 bg-zinc-900/50">
        {loading && <div className="px-4 py-14 text-center text-sm text-zinc-400">Fetching catalog entries…</div>}
        {message && <div role="alert" className="space-y-3 px-4 py-10 text-center">
          <p className="text-sm text-red-300">{message}</p>
          <button type="button" onClick={() => setRetry((value) => value + 1)} className={buttonClass}>Retry</button>
        </div>}
        {invalidMagnitude && <p className="px-4 py-14 text-center text-sm text-zinc-400">Check your magnitude filters above.</p>}
        {page && !invalidMagnitude && page.results.length === 0 && <div className="space-y-3 px-4 py-10 text-center">
          <p className="text-sm text-zinc-300">No objects match these filters.</p>
          <button type="button" onClick={reset} className={buttonClass}>Show all objects</button>
        </div>}
        {page && !invalidMagnitude && page.results.length > 0 && <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Catalog objects. Select an object name to view its details. Column headings sort the list.</caption>
            <thead className="border-b border-zinc-700 bg-zinc-900 text-xs text-zinc-300">
              <tr>
                {column("Name", "name")}{column("Type", "type")}
                <th scope="col" className="px-3 py-3 font-medium">Image</th>
                {column("Mag.", "magnitude", "hidden sm:table-cell")}
                {column("Redshift", "redshift", "hidden xl:table-cell")}
                {column("RA (°)", "ra", "hidden lg:table-cell")}
                {column("Dec (°)", "dec", "hidden lg:table-cell")}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {page.results.map((object) => <tr key={object.object_uuid} className="hover:bg-zinc-800/70 focus-within:bg-zinc-800/70">
                <th scope="row" className="px-3 py-3 font-medium">
                  <Link href={`/objects/${object.object_uuid}`} prefetch={false}
                    className="inline-block rounded text-indigo-300 underline decoration-indigo-400/30 underline-offset-4 hover:text-indigo-200 focus-visible:outline-2 focus-visible:outline-indigo-400">
                    {object.catalog_object_name || `Unnamed ${object.object_uuid.slice(0, 8)}`}
                  </Link>
                  {object.constellation && <span className="mt-1 block text-xs font-normal text-zinc-500">{object.constellation}</span>}
                </th>
                <td className="px-3 py-3 text-zinc-300 capitalize">{readableType(object.classified_object_type)}</td>
                <td className="px-3 py-3 text-xs"><span className={object.has_image ? "text-emerald-300" : "text-zinc-400"}>{object.has_image ? "Ready" : "Queued"}</span></td>
                <td className="hidden px-3 py-3 text-zinc-300 tabular-nums sm:table-cell">{object.catalog_magnitude?.toFixed(2) ?? "—"}</td>
                <td className="hidden px-3 py-3 text-zinc-300 tabular-nums xl:table-cell">{object.catalog_redshift?.toFixed(5) ?? "—"}</td>
                <td className="hidden px-3 py-3 text-zinc-300 tabular-nums lg:table-cell">{object.sky_coordinate_ra_degrees.toFixed(4)}</td>
                <td className="hidden px-3 py-3 text-zinc-300 tabular-nums lg:table-cell">{object.sky_coordinate_dec_degrees.toFixed(4)}</td>
              </tr>)}
            </tbody>
          </table>
        </div>}
      </div>

      {page && page.total_count > 0 && <nav aria-label="Catalog pages" className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <button type="button" className={buttonClass} disabled={currentPage === 1} onClick={() => goToPage(1)}>First</button>
        <button type="button" className={buttonClass} disabled={currentPage === 1} onClick={() => goToPage(currentPage - 1)}>Previous</button>
        <form onSubmit={jumpToPage} className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-zinc-300">
            Page
            <input key={currentPage} name="page" type="number" min={1} max={totalPages} step={1} required
              defaultValue={currentPage} aria-label="Page number" className={`${controlClass} w-20`} />
            <span className="whitespace-nowrap">of {totalPages.toLocaleString()}</span>
          </label>
          <button type="submit" className={buttonClass}>Go</button>
        </form>
        <button type="button" className={buttonClass} disabled={currentPage >= totalPages} onClick={() => goToPage(currentPage + 1)}>Next</button>
        <button type="button" className={buttonClass} disabled={currentPage >= totalPages} onClick={() => goToPage(totalPages)}>Last</button>
      </nav>}
      <p className="mt-3 text-xs text-zinc-400">Queued objects already have catalog details; their survey imagery is still being added. — means an unknown value.</p>
    </section>
  );
}
