"use client";

interface ViewerToolbarProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onGoHome: () => void;
  onToggleFullscreen: () => void;
  onToggleNavigator: () => void;
}

/**
 * Vertical toolbar with zoom, home, fullscreen, and navigator toggle buttons.
 *
 * Positioned on the left side of the viewer. Uses simple SVG icons
 * (no icon library dependency). Calls imperative viewer methods
 * via callback props from the parent.
 */
export default function ViewerToolbar({
  onZoomIn,
  onZoomOut,
  onGoHome,
  onToggleFullscreen,
  onToggleNavigator,
}: ViewerToolbarProps) {
  const buttonClass =
    "w-9 h-9 flex items-center justify-center rounded bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors";

  return (
    <div className="absolute top-4 left-4 flex flex-col gap-2 z-10">
      {/* Zoom In */}
      <button onClick={onZoomIn} className={buttonClass} title="Zoom in">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <line x1="8" y1="3" x2="8" y2="13" />
          <line x1="3" y1="8" x2="13" y2="8" />
        </svg>
      </button>

      {/* Zoom Out */}
      <button onClick={onZoomOut} className={buttonClass} title="Zoom out">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <line x1="3" y1="8" x2="13" y2="8" />
        </svg>
      </button>

      {/* Home / Fit View */}
      <button onClick={onGoHome} className={buttonClass} title="Fit to view">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M2 8 L8 2 L14 8" />
          <path d="M4 7 L4 14 L12 14 L12 7" />
        </svg>
      </button>

      {/* Fullscreen Toggle */}
      <button
        onClick={onToggleFullscreen}
        className={buttonClass}
        title="Toggle fullscreen"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M2 6 L2 2 L6 2" />
          <path d="M10 2 L14 2 L14 6" />
          <path d="M14 10 L14 14 L10 14" />
          <path d="M6 14 L2 14 L2 10" />
        </svg>
      </button>

      {/* Navigator Toggle */}
      <button
        onClick={onToggleNavigator}
        className={buttonClass}
        title="Toggle mini-map"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <rect x="2" y="2" width="12" height="12" rx="1" />
          <rect x="8" y="8" width="5" height="5" rx="0.5" />
        </svg>
      </button>
    </div>
  );
}
