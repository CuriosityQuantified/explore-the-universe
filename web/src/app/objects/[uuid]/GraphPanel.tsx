"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { fetchGraphNeighbors } from "@/lib/api";
import type { GraphNeighborNode, GraphNeighbors } from "@/types/object";

function NeighborCard({ node }: { node: GraphNeighborNode }) {
  return (
    <Link
      href={`/objects/${node.uuid}`}
      className="flex flex-col items-center gap-1 group"
    >
      {node.thumbnail_url ? (
        <Image
          src={node.thumbnail_url}
          alt={node.type ?? node.uuid}
          width={64}
          height={64}
          className="rounded object-cover bg-zinc-800 group-hover:opacity-80 transition-opacity"
          unoptimized
        />
      ) : (
        <div className="w-16 h-16 rounded bg-zinc-800 flex items-center justify-center text-zinc-600 text-xs">
          no img
        </div>
      )}
      <span className="text-blue-400 group-hover:underline text-xs truncate max-w-[64px]">
        {node.type ?? node.uuid.slice(0, 8)}
      </span>
    </Link>
  );
}

export function GraphPanel({ uuid }: { uuid: string }) {
  const [data, setData] = useState<GraphNeighbors | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchGraphNeighbors(uuid)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [uuid]);

  if (loading) return <p className="text-zinc-500 text-sm">Loading knowledge graph…</p>;
  if (error) return <p className="text-zinc-500 text-sm">Knowledge graph unavailable.</p>;
  if (!data || !data.in_graph) {
    return <p className="text-zinc-500 text-sm">Not yet in knowledge graph.</p>;
  }

  return (
    <div className="space-y-4">
      {data.contains_children.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Contains</h3>
          <div className="flex flex-wrap gap-3">
            {data.contains_children.map((n) => (
              <NeighborCard key={n.uuid} node={n} />
            ))}
          </div>
        </div>
      )}
      {data.contained_by.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Contained by</h3>
          <div className="flex flex-wrap gap-3">
            {data.contained_by.map((n) => (
              <NeighborCard key={n.uuid} node={n} />
            ))}
          </div>
        </div>
      )}
      {data.catalog_entries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Catalog identities</h3>
          <ul className="text-sm space-y-1">
            {data.catalog_entries.map((c, i) => (
              <li key={i} className="text-zinc-300">
                <span className="text-zinc-400">{c.catalog}:</span> {c.source_id}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
