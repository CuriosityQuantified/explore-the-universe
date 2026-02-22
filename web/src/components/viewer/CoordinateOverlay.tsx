"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { formatCoordinates } from "@/lib/coordinates";

interface CoordinateOverlayProps {
  hasWcs: boolean;
}

/**
 * Real-time RA/Dec coordinate display HUD.
 *
 * The live coordinate text is updated imperatively by the parent
 * (via updateLiveCoordinates) to avoid React re-renders at 30fps.
 * The pinned coordinate and display mode toggle use normal React state.
 */
export default function CoordinateOverlay({ hasWcs }: CoordinateOverlayProps) {
  const [displayMode, setDisplayMode] = useState<"hms" | "decimal">("hms");
  const [pinnedCoordinate, setPinnedCoordinate] = useState<{
    ra: number;
    dec: number;
  } | null>(null);
  const [showCopyToast, setShowCopyToast] = useState(false);
  const liveCoordRef = useRef<HTMLSpanElement>(null);
  const displayModeRef = useRef(displayMode);
  displayModeRef.current = displayMode;

  const toggleDisplayMode = useCallback(() => {
    setDisplayMode((prev) => (prev === "hms" ? "decimal" : "hms"));
  }, []);

  // Re-format pinned coordinate when display mode changes
  const pinnedText =
    pinnedCoordinate
      ? formatCoordinates(pinnedCoordinate.ra, pinnedCoordinate.dec, displayMode)
      : null;

  const handleCopyPinned = useCallback(async () => {
    if (!pinnedCoordinate) return;
    const text = formatCoordinates(
      pinnedCoordinate.ra,
      pinnedCoordinate.dec,
      displayModeRef.current,
    );
    try {
      await navigator.clipboard.writeText(text);
      setShowCopyToast(true);
    } catch {
      // Clipboard API may fail in non-secure contexts -- silently ignore
    }
  }, [pinnedCoordinate]);

  // Auto-hide copy toast after 2 seconds
  useEffect(() => {
    if (!showCopyToast) return;
    const timer = setTimeout(() => setShowCopyToast(false), 2000);
    return () => clearTimeout(timer);
  }, [showCopyToast]);

  if (!hasWcs) {
    return (
      <div className="absolute bottom-0 left-0 right-0 bg-black/70 px-4 py-2 text-sm text-zinc-500">
        WCS data unavailable
      </div>
    );
  }

  return (
    <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm px-4 py-2 flex items-center gap-4 text-sm font-mono">
      {/* Live coordinate readout (updated imperatively by parent) */}
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
            onClick={handleCopyPinned}
            className="px-1.5 py-0.5 rounded text-xs bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
            title="Copy to clipboard"
          >
            {/* Simple copy icon using unicode */}
            &#x2398;
          </button>
        </div>
      )}

      {/* Copy toast notification */}
      {showCopyToast && (
        <span className="text-xs text-green-400 animate-pulse">
          Copied!
        </span>
      )}
    </div>
  );
}

/**
 * Update the live coordinate display without triggering a React re-render.
 *
 * Called from the parent component's onCoordinateChange callback at ~30fps.
 * Directly mutates the DOM text content of the live coordinate span.
 */
export function updateLiveCoordinates(
  element: HTMLSpanElement | null,
  ra: number,
  dec: number,
  mode: "hms" | "decimal",
): void {
  if (!element) return;
  element.textContent = formatCoordinates(ra, dec, mode);
}

/**
 * Pin a coordinate from a click event.
 *
 * This is designed to be called as a setter from the parent, which holds
 * a ref to the CoordinateOverlay and calls this when the user clicks
 * in the viewer. However, since we use React state for pinned coordinates,
 * the parent should call the setPinnedCoordinate exposed via ref.
 */
export type CoordinateOverlayHandle = {
  liveCoordElement: HTMLSpanElement | null;
  pinCoordinate: (ra: number, dec: number) => void;
  displayMode: "hms" | "decimal";
};
