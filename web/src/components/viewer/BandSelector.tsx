"use client";

interface BandSelectorProps {
  spectralFilters: string[] | null;
  currentBand: number;
  onBandChange: (index: number) => void;
}

/**
 * Filter/band switcher for multi-band observations.
 *
 * Renders tabs showing available spectral filter names (e.g., "F200W", "F444W").
 * If the observation has only one filter or null filters, renders nothing.
 *
 * LIMITATION (Phase 3): The Phase 2 tiling pipeline currently overwrites tiles
 * for each FITS file using the same S3 prefix ({uuid}/tiles/). This means only
 * the LAST processed file's tiles exist in MinIO. Switching bands in this UI
 * will reload the same tile set. The band selector is built and wired so it's
 * ready when tile isolation is added (likely Phase 6 or a future fix), at which
 * point the tile URL will change to {uuid}/{band_index}/tiles/.
 *
 * @param spectralFilters - Array of filter names from the observation, or null
 * @param currentBand - Currently selected band index (0-based)
 * @param onBandChange - Callback to switch the active band (triggers tile reload)
 */
export default function BandSelector({
  spectralFilters,
  currentBand,
  onBandChange,
}: BandSelectorProps) {
  // Don't render for single-band or unknown-band observations
  if (!spectralFilters || spectralFilters.length <= 1) {
    return null;
  }

  return (
    <div className="absolute top-4 right-4 flex items-center gap-1 bg-zinc-900/90 backdrop-blur-sm border border-zinc-700/50 rounded-lg px-1 py-1 z-20">
      {spectralFilters.map((filter, index) => (
        <button
          key={filter}
          onClick={() => onBandChange(index)}
          className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
            index === currentBand
              ? "bg-cyan-700/80 text-cyan-100"
              : "text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
          }`}
          title={`Switch to ${filter} band`}
        >
          {filter}
        </button>
      ))}
    </div>
  );
}
