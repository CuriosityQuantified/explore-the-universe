"use client";

import { useRef, useState, useCallback } from "react";
import type OpenSeadragon from "openseadragon";
import type {
  WcsParams,
  TileMetadata,
  ObservationDetail,
} from "@/types/observation";
import { formatCoordinates } from "@/lib/coordinates";
import SkyViewer, { type SkyViewerHandle } from "@/components/viewer/SkyViewer";
import CoordinateOverlay from "@/components/viewer/CoordinateOverlay";
import ViewerToolbar from "@/components/viewer/ViewerToolbar";
import ScaleBar from "@/components/viewer/ScaleBar";

interface ViewerClientProps {
  observationUuid: string;
  wcsParams: WcsParams;
  tileMetadata: TileMetadata;
  tileBaseUrl: string;
  observationDetail: ObservationDetail;
}

/**
 * Client-side viewer wrapper that composes SkyViewer, CoordinateOverlay,
 * ViewerToolbar, and ScaleBar. This is the root "use client" boundary
 * for the viewer page.
 *
 * Coordinate updates from mouse movement are pushed to the CoordinateOverlay
 * via direct DOM mutation (liveCoordRef) to avoid React re-renders at 30fps.
 */
export default function ViewerClient({
  observationUuid,
  wcsParams,
  tileMetadata,
  tileBaseUrl,
  observationDetail,
}: ViewerClientProps) {
  const skyViewerRef = useRef<SkyViewerHandle>(null);
  const liveCoordRef = useRef<HTMLSpanElement>(null);
  const [viewer, setViewer] = useState<OpenSeadragon.Viewer | null>(null);
  const [displayMode, setDisplayMode] = useState<"hms" | "decimal">("hms");
  const [pinnedCoordinate, setPinnedCoordinate] = useState<{
    ra: number;
    dec: number;
  } | null>(null);
  const [showCopyToast, setShowCopyToast] = useState(false);

  // Stable ref for display mode so imperative updates use the current value
  const displayModeRef = useRef(displayMode);
  displayModeRef.current = displayMode;

  // Called at ~30fps from SkyViewer mouse tracker -- directly mutates DOM
  const handleCoordinateChange = useCallback(
    (ra: number, dec: number) => {
      if (liveCoordRef.current) {
        liveCoordRef.current.textContent = formatCoordinates(
          ra,
          dec,
          displayModeRef.current,
        );
      }
    },
    [],
  );

  // Called on click -- pins coordinate and copies to clipboard
  const handleCoordinateClick = useCallback(
    (ra: number, dec: number) => {
      setPinnedCoordinate({ ra, dec });
      const text = formatCoordinates(ra, dec, displayModeRef.current);
      navigator.clipboard.writeText(text).then(() => {
        setShowCopyToast(true);
        setTimeout(() => setShowCopyToast(false), 2000);
      }).catch(() => {
        // Clipboard API may not be available in all contexts
      });
    },
    [],
  );

  const handleViewerReady = useCallback((v: OpenSeadragon.Viewer) => {
    setViewer(v);
  }, []);

  const toggleDisplayMode = useCallback(() => {
    setDisplayMode((prev) => (prev === "hms" ? "decimal" : "hms"));
  }, []);

  const pinnedText = pinnedCoordinate
    ? formatCoordinates(pinnedCoordinate.ra, pinnedCoordinate.dec, displayMode)
    : null;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black">
      {/* OpenSeadragon viewer fills the entire viewport */}
      <SkyViewer
        ref={skyViewerRef}
        observationUuid={observationUuid}
        wcsParams={wcsParams}
        tileMetadata={tileMetadata}
        tileBaseUrl={tileBaseUrl}
        onCoordinateChange={handleCoordinateChange}
        onCoordinateClick={handleCoordinateClick}
        onViewerReady={handleViewerReady}
      />

      {/* Toolbar: left side */}
      <ViewerToolbar
        onZoomIn={() => skyViewerRef.current?.zoomIn()}
        onZoomOut={() => skyViewerRef.current?.zoomOut()}
        onGoHome={() => skyViewerRef.current?.goHome()}
        onToggleFullscreen={() => skyViewerRef.current?.toggleFullscreen()}
        onToggleNavigator={() => skyViewerRef.current?.toggleNavigator()}
      />

      {/* Scale bar: bottom-right */}
      <ScaleBar viewer={viewer} wcsParams={wcsParams} />

      {/* Coordinate overlay: bottom */}
      <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm px-4 py-2 flex items-center gap-4 text-sm font-mono z-10">
        {/* Live coordinate readout */}
        <div className="flex items-center gap-2">
          <span className="text-zinc-500">RA/Dec:</span>
          <span ref={liveCoordRef} className="text-zinc-200">
            --
          </span>
        </div>

        {/* Display mode toggle */}
        <button
          onClick={toggleDisplayMode}
          className="px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
        >
          {displayMode === "hms" ? "HMS" : "DEG"}
        </button>

        {/* Pinned coordinate */}
        {pinnedText && (
          <div className="flex items-center gap-2 border-l border-zinc-700 pl-4">
            <span className="text-zinc-500">Pinned:</span>
            <span className="text-amber-400">{pinnedText}</span>
            <button
              onClick={() => {
                if (pinnedCoordinate) {
                  navigator.clipboard.writeText(pinnedText).catch(() => {});
                  setShowCopyToast(true);
                  setTimeout(() => setShowCopyToast(false), 2000);
                }
              }}
              className="px-1.5 py-0.5 rounded text-xs bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
              title="Copy to clipboard"
            >
              &#x2398;
            </button>
          </div>
        )}

        {/* Copy toast */}
        {showCopyToast && (
          <span className="text-xs text-green-400 animate-pulse">
            Copied!
          </span>
        )}

        {/* Observation info: right side */}
        <div className="ml-auto text-xs text-zinc-500">
          {observationDetail.telescope_name} /{" "}
          {observationDetail.instrument_name}
        </div>
      </div>
    </div>
  );
}
