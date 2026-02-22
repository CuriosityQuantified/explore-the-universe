"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import OpenSeadragon from "openseadragon";
import type {
  WcsParams,
  TileMetadata,
  ObservationDetail,
} from "@/types/observation";
import { formatCoordinates } from "@/lib/coordinates";
import SkyViewer, { type SkyViewerHandle } from "@/components/viewer/SkyViewer";
import ViewerToolbar from "@/components/viewer/ViewerToolbar";
import ScaleBar from "@/components/viewer/ScaleBar";
import ObservationInfo from "@/components/viewer/ObservationInfo";
import ImageAdjustments, {
  type ImageAdjustmentValues,
  buildCssFilter,
} from "@/components/viewer/ImageAdjustments";
import BandSelector from "@/components/viewer/BandSelector";
import CoordinateGrid from "@/components/viewer/CoordinateGrid";

interface ViewerClientProps {
  observationUuid: string;
  wcsParams: WcsParams;
  tileMetadata: TileMetadata;
  tileBaseUrl: string;
  observationDetail: ObservationDetail;
}

/**
 * Client-side viewer wrapper composing all viewer sub-components:
 * SkyViewer, ViewerToolbar, ScaleBar, ObservationInfo, ImageAdjustments,
 * BandSelector, and CoordinateGrid.
 *
 * This is the root "use client" boundary for the viewer page.
 *
 * Coordinate updates from mouse movement are pushed to the coordinate
 * overlay via direct DOM mutation (liveCoordRef) to avoid React re-renders
 * at ~30fps.
 *
 * Image adjustments are applied as CSS filters on the OpenSeadragon canvas
 * element via viewer.canvas.style.filter, combining brightness, contrast,
 * gamma approximation, and invert.
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

  // Panel toggle states (all hidden by default per CONTEXT.md)
  const [isInfoOpen, setIsInfoOpen] = useState(false);
  const [isAdjustmentsOpen, setIsAdjustmentsOpen] = useState(false);
  const [isGridVisible, setIsGridVisible] = useState(false);
  const [currentBand, setCurrentBand] = useState(0);

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
      navigator.clipboard
        .writeText(text)
        .then(() => {
          setShowCopyToast(true);
          setTimeout(() => setShowCopyToast(false), 2000);
        })
        .catch(() => {
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

  // Apply CSS filter to OSD canvas when adjustments change
  const handleAdjustmentChange = useCallback(
    (adjustments: ImageAdjustmentValues) => {
      if (!viewer) return;
      const canvas = viewer.canvas as HTMLElement;
      if (canvas) {
        canvas.style.filter = buildCssFilter(adjustments);
      }
    },
    [viewer],
  );

  // Band change handler -- reloads tile source (future: different S3 prefix per band)
  const handleBandChange = useCallback(
    (index: number) => {
      setCurrentBand(index);
      // NOTE: Currently all bands share the same tile prefix in MinIO due to
      // Phase 2 overwriting. When tile isolation is added (Phase 6 or future fix),
      // this would update the tile source URL to {uuid}/{band_index}/tiles/.
      // For now, switching bands triggers no visual change -- the same tiles reload.
    },
    [],
  );

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

      {/* Coordinate grid overlay (SVG on top of OSD) */}
      <CoordinateGrid
        viewer={viewer}
        wcsParams={wcsParams}
        visible={isGridVisible}
      />

      {/* Toolbar: left side with all toggle buttons */}
      <ViewerToolbar
        onZoomIn={() => skyViewerRef.current?.zoomIn()}
        onZoomOut={() => skyViewerRef.current?.zoomOut()}
        onGoHome={() => skyViewerRef.current?.goHome()}
        onToggleFullscreen={() => skyViewerRef.current?.toggleFullscreen()}
        onToggleNavigator={() => skyViewerRef.current?.toggleNavigator()}
        onToggleInfo={() => setIsInfoOpen((prev) => !prev)}
        onToggleAdjustments={() => setIsAdjustmentsOpen((prev) => !prev)}
        onToggleGrid={() => setIsGridVisible((prev) => !prev)}
        isInfoOpen={isInfoOpen}
        isAdjustmentsOpen={isAdjustmentsOpen}
        isGridVisible={isGridVisible}
      />

      {/* Image adjustments panel: left side, next to toolbar */}
      <ImageAdjustments
        onAdjustmentChange={handleAdjustmentChange}
        isOpen={isAdjustmentsOpen}
        onToggle={() => setIsAdjustmentsOpen(false)}
      />

      {/* Band selector: top-right (only renders for multi-band observations) */}
      <BandSelector
        spectralFilters={observationDetail.spectral_filters}
        currentBand={currentBand}
        onBandChange={handleBandChange}
      />

      {/* Observation info sidebar: right side */}
      <ObservationInfo
        observation={observationDetail}
        isOpen={isInfoOpen}
        onToggle={() => setIsInfoOpen(false)}
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
