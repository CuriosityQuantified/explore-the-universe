"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import OpenSeadragon from "openseadragon";
import type { WcsParams } from "@/types/observation";
import { pixelToRaDec } from "@/lib/wcs";

interface CoordinateGridProps {
  viewer: OpenSeadragon.Viewer | null;
  wcsParams: WcsParams;
  visible: boolean;
}

/** Predefined "nice" grid spacings in arcseconds, from fine to coarse. */
const NICE_GRID_ARCSEC = [
  1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 18000,
  36000,
];

/** Target number of grid lines across the viewport. */
const TARGET_GRID_LINES = 5;

interface GridLine {
  /** SVG path data string (d attribute) */
  path: string;
  /** Label text (e.g., "05h 35m" for RA, "+23d 30'" for Dec) */
  label: string;
  /** Label position in viewport pixels */
  labelX: number;
  labelY: number;
  /** Whether this is a RA (vertical) or Dec (horizontal) line */
  type: "ra" | "dec";
}

/**
 * RA/Dec coordinate grid overlay rendered as SVG on top of OpenSeadragon.
 *
 * When visible, computes grid line positions by:
 * 1. Getting viewport bounds from OSD and converting to RA/Dec
 * 2. Choosing a "nice" grid spacing based on field of view
 * 3. For each grid line, sampling multiple points and converting back to
 *    viewport coordinates via inverse WCS
 * 4. Drawing SVG paths and edge labels
 *
 * Listens to viewer `animation` and `animation-finish` events to re-render
 * on pan/zoom. Off by default per CONTEXT.md.
 */
export default function CoordinateGrid({
  viewer,
  wcsParams,
  visible,
}: CoordinateGridProps) {
  const [gridLines, setGridLines] = useState<GridLine[]>([]);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const rafRef = useRef<number>(0);

  /**
   * Approximate inverse WCS: RA/Dec -> image pixel coordinates.
   *
   * For the TAN (gnomonic) projection, the inverse is:
   *   1. Spherical rotation: celestial -> native spherical
   *   2. TAN projection: native spherical -> intermediate world coords
   *   3. Inverse CD matrix: intermediate -> pixel offset
   *   4. Add CRPIX to get pixel coordinates
   */
  const raDecToPixel = useCallback(
    (raDeg: number, decDeg: number): { x: number; y: number } => {
      const deg2rad = Math.PI / 180;
      const ra = raDeg * deg2rad;
      const dec = decDeg * deg2rad;
      const ra0 = wcsParams.crval1 * deg2rad;
      const dec0 = wcsParams.crval2 * deg2rad;

      // Spherical rotation to native coordinates
      const sinDec = Math.sin(dec);
      const cosDec = Math.cos(dec);
      const sinDec0 = Math.sin(dec0);
      const cosDec0 = Math.cos(dec0);
      const deltaRa = ra - ra0;
      const cosDeltaRa = Math.cos(deltaRa);
      const sinDeltaRa = Math.sin(deltaRa);

      // TAN projection (gnomonic)
      const denom = sinDec * sinDec0 + cosDec * cosDec0 * cosDeltaRa;
      if (denom <= 0) {
        // Point is behind the tangent plane
        return { x: -9999, y: -9999 };
      }

      const xiDeg = (cosDec * sinDeltaRa) / denom / deg2rad;
      const etaDeg =
        (sinDec * cosDec0 - cosDec * sinDec0 * cosDeltaRa) / denom / deg2rad;

      // Inverse CD matrix: [dx, dy] = CD^-1 * [xi, eta]
      const det =
        wcsParams.cd1_1 * wcsParams.cd2_2 -
        wcsParams.cd1_2 * wcsParams.cd2_1;
      if (Math.abs(det) < 1e-20) {
        return { x: -9999, y: -9999 };
      }

      const dx = (wcsParams.cd2_2 * xiDeg - wcsParams.cd1_2 * etaDeg) / det;
      const dy = (-wcsParams.cd2_1 * xiDeg + wcsParams.cd1_1 * etaDeg) / det;

      return {
        x: dx + wcsParams.crpix1,
        y: dy + wcsParams.crpix2,
      };
    },
    [wcsParams],
  );

  /**
   * Convert image pixel coords (FITS convention) to viewport pixel coords.
   * Accounts for the FITS Y-flip (FITS origin is bottom-left, image top-left).
   */
  const imageToViewportPixel = useCallback(
    (
      fitsX: number,
      fitsY: number,
    ): { screenX: number; screenY: number } | null => {
      if (!viewer?.viewport) return null;

      // FITS Y-flip: image Y = naxis2 - fitsY
      const imageY = wcsParams.naxis2 - fitsY;
      const imagePoint = new OpenSeadragon.Point(fitsX, imageY);
      const viewportPoint =
        viewer.viewport.imageToViewportCoordinates(imagePoint);
      const screenPoint = viewer.viewport.viewportToViewerElementCoordinates(
        viewportPoint,
      );
      return { screenX: screenPoint.x, screenY: screenPoint.y };
    },
    [viewer, wcsParams.naxis2],
  );

  const computeGrid = useCallback(() => {
    if (!viewer?.viewport || !visible) {
      setGridLines([]);
      return;
    }

    const containerSize = viewer.viewport.getContainerSize();
    setViewportSize({ width: containerSize.x, height: containerSize.y });

    // Get RA/Dec at the four viewport corners
    const corners = [
      { sx: 0, sy: 0 },
      { sx: containerSize.x, sy: 0 },
      { sx: 0, sy: containerSize.y },
      { sx: containerSize.x, sy: containerSize.y },
    ];

    const cornerRaDecs = corners.map((c) => {
      const viewerPoint = new OpenSeadragon.Point(c.sx, c.sy);
      const viewportPoint =
        viewer.viewport.viewerElementToViewportCoordinates(viewerPoint);
      const imagePoint =
        viewer.viewport.viewportToImageCoordinates(viewportPoint);
      const fitsX = imagePoint.x;
      const fitsY = wcsParams.naxis2 - imagePoint.y;
      return pixelToRaDec(fitsX, fitsY, wcsParams);
    });

    // Compute field of view extent
    const ras = cornerRaDecs.map((c) => c.ra);
    const decs = cornerRaDecs.map((c) => c.dec);

    let raMin = Math.min(...ras);
    let raMax = Math.max(...ras);
    const decMin = Math.min(...decs);
    const decMax = Math.max(...decs);

    // Handle RA wrapping around 0/360
    if (raMax - raMin > 180) {
      // Wrap: shift values < 180 up by 360
      const shifted = ras.map((r) => (r < 180 ? r + 360 : r));
      raMin = Math.min(...shifted) % 360;
      raMax = Math.max(...shifted) % 360;
    }

    const decFov = decMax - decMin;
    const raFov = raMax > raMin ? raMax - raMin : raMax + 360 - raMin;
    const fovArcsec = Math.max(decFov, raFov) * 3600;

    // Choose grid spacing: pick the largest "nice" value that gives at least TARGET_GRID_LINES
    let gridSpacingArcsec = NICE_GRID_ARCSEC[0];
    for (const spacing of NICE_GRID_ARCSEC) {
      if (fovArcsec / spacing >= TARGET_GRID_LINES) {
        gridSpacingArcsec = spacing;
      } else {
        break;
      }
    }

    const gridSpacingDeg = gridSpacingArcsec / 3600;
    const lines: GridLine[] = [];
    const numSamples = 20; // Points per grid line for smooth curves

    // Generate constant-Dec (horizontal) lines
    const decStart =
      Math.floor(decMin / gridSpacingDeg) * gridSpacingDeg;
    for (
      let dec = decStart;
      dec <= decMax + gridSpacingDeg;
      dec += gridSpacingDeg
    ) {
      if (dec < -90 || dec > 90) continue;

      const points: { screenX: number; screenY: number }[] = [];
      for (let i = 0; i <= numSamples; i++) {
        const ra = raMin + (raFov * i) / numSamples;
        const normalizedRa = ((ra % 360) + 360) % 360;
        const pixel = raDecToPixel(normalizedRa, dec);
        const screen = imageToViewportPixel(pixel.x, pixel.y);
        if (screen && screen.screenX > -1000 && screen.screenY > -1000) {
          points.push(screen);
        }
      }

      if (points.length >= 2) {
        const pathData = points
          .map((p, i) =>
            i === 0
              ? `M ${p.screenX.toFixed(1)} ${p.screenY.toFixed(1)}`
              : `L ${p.screenX.toFixed(1)} ${p.screenY.toFixed(1)}`,
          )
          .join(" ");

        lines.push({
          path: pathData,
          label: formatDecLabel(dec, gridSpacingArcsec),
          labelX: points[0].screenX + 4,
          labelY: points[0].screenY - 4,
          type: "dec",
        });
      }
    }

    // Generate constant-RA (vertical) lines
    const raStart =
      Math.floor(raMin / gridSpacingDeg) * gridSpacingDeg;
    for (
      let ra = raStart;
      ra <= raMin + raFov + gridSpacingDeg;
      ra += gridSpacingDeg
    ) {
      const normalizedRa = ((ra % 360) + 360) % 360;

      const points: { screenX: number; screenY: number }[] = [];
      for (let i = 0; i <= numSamples; i++) {
        const dec = decMin + (decFov * i) / numSamples;
        if (dec < -90 || dec > 90) continue;
        const pixel = raDecToPixel(normalizedRa, dec);
        const screen = imageToViewportPixel(pixel.x, pixel.y);
        if (screen && screen.screenX > -1000 && screen.screenY > -1000) {
          points.push(screen);
        }
      }

      if (points.length >= 2) {
        const pathData = points
          .map((p, i) =>
            i === 0
              ? `M ${p.screenX.toFixed(1)} ${p.screenY.toFixed(1)}`
              : `L ${p.screenX.toFixed(1)} ${p.screenY.toFixed(1)}`,
          )
          .join(" ");

        lines.push({
          path: pathData,
          label: formatRaLabel(normalizedRa, gridSpacingArcsec),
          labelX: points[points.length - 1].screenX + 4,
          labelY: points[points.length - 1].screenY - 4,
          type: "ra",
        });
      }
    }

    setGridLines(lines);
  }, [
    viewer,
    visible,
    wcsParams,
    raDecToPixel,
    imageToViewportPixel,
  ]);

  // Listen to viewer events and re-render grid on pan/zoom
  useEffect(() => {
    if (!viewer || !visible) {
      setGridLines([]);
      return;
    }

    const handler = () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
      rafRef.current = requestAnimationFrame(() => {
        computeGrid();
      });
    };

    viewer.addHandler("animation", handler);
    viewer.addHandler("animation-finish", handler);
    viewer.addHandler("open", handler);
    viewer.addHandler("resize", handler);

    // Initial computation
    computeGrid();

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
      viewer.removeHandler("animation", handler);
      viewer.removeHandler("animation-finish", handler);
      viewer.removeHandler("open", handler);
      viewer.removeHandler("resize", handler);
    };
  }, [viewer, visible, computeGrid]);

  if (!visible || gridLines.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none z-10"
      width={viewportSize.width}
      height={viewportSize.height}
      style={{ overflow: "hidden" }}
    >
      {gridLines.map((line, i) => (
        <g key={i}>
          <path
            d={line.path}
            fill="none"
            stroke={line.type === "ra" ? "rgba(0, 200, 255, 0.25)" : "rgba(0, 200, 255, 0.25)"}
            strokeWidth="0.5"
            strokeDasharray={line.type === "ra" ? "4 4" : "4 4"}
          />
          <text
            x={line.labelX}
            y={line.labelY}
            fill="rgba(0, 200, 255, 0.6)"
            fontSize="9"
            fontFamily="monospace"
          >
            {line.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** Format RA label based on grid spacing. */
function formatRaLabel(raDeg: number, spacingArcsec: number): string {
  const totalHours = raDeg / 15;
  const hours = Math.floor(totalHours);
  const remainingMinutes = (totalHours - hours) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  const h = String(hours).padStart(2, "0");
  const m = String(minutes).padStart(2, "0");

  if (spacingArcsec >= 3600) {
    return `${h}h`;
  }
  if (spacingArcsec >= 60) {
    return `${h}h${m}m`;
  }
  return `${h}h${m}m${seconds.toFixed(0).padStart(2, "0")}s`;
}

/** Format Dec label based on grid spacing. */
function formatDecLabel(decDeg: number, spacingArcsec: number): string {
  const sign = decDeg >= 0 ? "+" : "-";
  const absDeg = Math.abs(decDeg);
  const deg = Math.floor(absDeg);
  const remainingMinutes = (absDeg - deg) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  const d = String(deg).padStart(2, "0");
  const m = String(minutes).padStart(2, "0");

  if (spacingArcsec >= 3600) {
    return `${sign}${d}d`;
  }
  if (spacingArcsec >= 60) {
    return `${sign}${d}d${m}'`;
  }
  return `${sign}${d}d${m}'${seconds.toFixed(0).padStart(2, "0")}"`;
}
