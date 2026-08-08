"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { searchByName, searchByCone, searchByType } from "@/lib/api";
import type { ObjectSearchItem, NameSearchResult } from "@/types/search";
import QueryBuilder from "@/components/QueryBuilder";

const PAGE_SIZE = 24;

// ---------------------------------------------------------------------------
// Thumbnail card
// ---------------------------------------------------------------------------

function ObjectCard({ obj }: { obj: ObjectSearchItem }) {
  return (
    <Link
      href={`/objects/${obj.object_uuid}`}
      className="group flex flex-col rounded bg-zinc-800 border border-zinc-700 hover:border-indigo-400 overflow-hidden transition-colors"
    >
      {/* Thumbnail */}
      <div className="w-full aspect-square bg-zinc-900 flex items-center justify-center overflow-hidden">
        {obj.cutout_thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={obj.cutout_thumbnail_url}
            alt={obj.catalog_object_name ?? obj.object_uuid}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-zinc-600 text-xs">No image</span>
        )}
      </div>

      {/* Info */}
      <div className="p-3 flex flex-col gap-1">
        <div className="flex items-center gap-2 flex-wrap">
          {obj.classified_object_type && (
            <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-indigo-900 text-indigo-200 shrink-0">
              {obj.classified_object_type}
            </span>
          )}
          {obj.is_anomaly_flagged && (
            <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-800 text-yellow-200 shrink-0">
              Anomaly
            </span>
          )}
        </div>
        <p className="text-sm text-zinc-200 truncate">
          {obj.catalog_object_name ?? <span className="text-zinc-500 italic">Unknown</span>}
        </p>
        <p className="text-xs text-zinc-500 font-mono truncate">
          {obj.object_uuid}
        </p>
      </div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Pagination controls
// ---------------------------------------------------------------------------

function Pagination({
  offset,
  total,
  limit,
  onPrev,
  onNext,
}: {
  offset: number;
  total: number;
  limit: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (total === 0) return null;

  return (
    <div className="flex items-center gap-4 justify-center mt-8">
      <button
        onClick={onPrev}
        disabled={offset === 0}
        className="rounded bg-zinc-700 px-4 py-2 text-sm font-medium text-zinc-200 hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        ← Prev
      </button>
      <span className="text-sm text-zinc-400">
        Page {page} of {totalPages} ({total} result{total !== 1 ? "s" : ""})
      </span>
      <button
        onClick={onNext}
        disabled={offset + limit >= total}
        className="rounded bg-zinc-700 px-4 py-2 text-sm font-medium text-zinc-200 hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Next →
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Search results inner component (needs useSearchParams)
// ---------------------------------------------------------------------------

function SearchResults() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const name = searchParams.get("name");
  const ra = searchParams.get("ra");
  const dec = searchParams.get("dec");
  const radiusArcsec = searchParams.get("radius_arcsec");
  const type = searchParams.get("type");

  const [offset, setOffset] = useState(0);
  const [results, setResults] = useState<ObjectSearchItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvedInfo, setResolvedInfo] = useState<{
    ra: number | null;
    dec: number | null;
    name: string | null;
  } | null>(null);

  // Structured (QueryBuilder) search results — override URL-driven results when set
  const [builderResults, setBuilderResults] = useState<ObjectSearchItem[] | null>(null);
  const [builderTotal, setBuilderTotal] = useState(0);
  const [builderOffset, setBuilderOffset] = useState(0);
  const [builderLoading, setBuilderLoading] = useState(false);
  const [builderError, setBuilderError] = useState<string | null>(null);

  // Reset offset when query changes
  useEffect(() => {
    setOffset(0);
  }, [name, ra, dec, radiusArcsec, type]);

  useEffect(() => {
    setLoading(true);
    setError(null);

    async function run() {
      try {
        if (name) {
          const res: NameSearchResult = await searchByName(name, PAGE_SIZE, offset);
          setResults(res.results);
          setTotal(res.total);
          setResolvedInfo({
            ra: res.resolved_ra,
            dec: res.resolved_dec,
            name: res.simbad_name,
          });
        } else if (ra && dec && radiusArcsec) {
          const res = await searchByCone(
            parseFloat(ra),
            parseFloat(dec),
            parseFloat(radiusArcsec),
            PAGE_SIZE,
            offset,
          );
          setResults(res.results);
          setTotal(res.total);
          setResolvedInfo(null);
        } else if (type) {
          const res = await searchByType(type, PAGE_SIZE, offset);
          setResults(res.results);
          setTotal(res.total);
          setResolvedInfo(null);
        } else {
          setError("No search parameters provided.");
          setLoading(false);
          return;
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Search failed";
        setError(msg);
      } finally {
        setLoading(false);
      }
    }

    run();
  }, [name, ra, dec, radiusArcsec, type, offset]);

  // --- Build title ---
  let title = "Search Results";
  if (name) title = `Results for "${name}"`;
  else if (type) title = `Type: ${type}`;
  else if (ra && dec) title = `Cone search RA=${ra} Dec=${dec} r=${radiusArcsec}″`;

  // Determine which result set to display: builder takes priority when active
  const showBuilder = builderResults !== null;
  const displayResults = showBuilder ? builderResults : results;
  const displayTotal = showBuilder ? builderTotal : total;
  const displayLoading = showBuilder ? builderLoading : loading;
  const displayError = showBuilder ? builderError : error;

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.push("/")}
          className="text-sm text-zinc-400 hover:text-zinc-200"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-semibold">{showBuilder ? "Filter Results" : title}</h1>
      </div>

      {/* QueryBuilder — always visible, results override URL-driven results when used */}
      <QueryBuilder
        onResults={(r, count) => {
          setBuilderResults(r);
          setBuilderTotal(count);
        }}
        onLoading={setBuilderLoading}
        onError={setBuilderError}
        offset={builderOffset}
        onOffsetReset={() => setBuilderOffset(0)}
      />

      {/* Resolved coordinates banner (name search, URL-driven only) */}
      {!showBuilder && resolvedInfo?.ra !== undefined && resolvedInfo.ra !== null && (
        <div className="mb-4 text-sm text-zinc-400 bg-zinc-800 rounded px-4 py-2">
          SIMBAD resolved{" "}
          <span className="text-zinc-200 font-medium">{resolvedInfo.name}</span>
          {" "}→ RA {resolvedInfo.ra?.toFixed(4)}°, Dec {resolvedInfo.dec?.toFixed(4)}°
          {" · "}5 arcsec search radius
        </div>
      )}

      {/* Loading */}
      {displayLoading && (
        <p className="text-zinc-500 text-sm">Searching…</p>
      )}

      {/* Error */}
      {!displayLoading && displayError && (
        <div className="rounded bg-red-900/40 border border-red-700 px-4 py-3 text-sm text-red-300">
          {displayError}
        </div>
      )}

      {/* Empty state */}
      {!displayLoading && !displayError && displayResults.length === 0 && (
        <div className="text-center py-16">
          <p className="text-zinc-400 text-lg">No objects found.</p>
          {!showBuilder && name && resolvedInfo?.ra === null && (
            <p className="text-zinc-500 text-sm mt-2">
              SIMBAD could not resolve &quot;{name}&quot;. Try a different name.
            </p>
          )}
        </div>
      )}

      {/* Results grid */}
      {!displayLoading && !displayError && displayResults.length > 0 && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {displayResults.map((obj) => (
              <ObjectCard key={obj.object_uuid} obj={obj} />
            ))}
          </div>

          <Pagination
            offset={showBuilder ? builderOffset : offset}
            total={displayTotal}
            limit={PAGE_SIZE}
            onPrev={() => showBuilder
              ? setBuilderOffset(Math.max(0, builderOffset - PAGE_SIZE))
              : setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => showBuilder
              ? setBuilderOffset(builderOffset + PAGE_SIZE)
              : setOffset(offset + PAGE_SIZE)}
          />
        </>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Page export — wraps in Suspense so useSearchParams works in Next.js 14
// ---------------------------------------------------------------------------

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <main className="max-w-6xl mx-auto px-4 py-8">
          <p className="text-zinc-500 text-sm">Loading…</p>
        </main>
      }
    >
      <SearchResults />
    </Suspense>
  );
}
