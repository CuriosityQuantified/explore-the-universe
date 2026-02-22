"use client";

import { useEffect, useState, useCallback } from "react";
import type OpenSeadragon from "openseadragon";
import type { WcsParams } from "@/types/observation";

interface ScaleBarProps {
  viewer: OpenSeadragon.Viewer | null;
  wcsParams: WcsParams;
}

/** Preset "nice" angular scale values in arcseconds. */
const NICE_ARCSEC_VALUES = [
  0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1200, 1800, 3600,
  7200, 18000, 36000,
];

/** Maximum bar width in CSS pixels. */
const MAX_BAR_WIDTH_PX = 200;

/**
 * Format arcseconds into a human-readable angular size label.
 */
function formatAngularSize(arcsec: number): string {
  if (arcsec >= 3600) {
    const deg = arcsec / 3600;
    return `${deg} deg`;
  }
  if (arcsec >= 60) {
    const arcmin = arcsec / 60;
    return `${arcmin} arcmin`;
  }
  if (arcsec >= 1) {
    return `${arcsec} arcsec`;
  }
  return `${(arcsec * 1000).toFixed(0)} mas`;
}

/**
 * Angular scale bar that updates with the viewer's zoom level.
 *
 * Computes the pixel scale from the WCS CD matrix, then picks a "nice"
 * angular value that fits within MAX_BAR_WIDTH_PX at the current zoom.
 * Positioned bottom-right of the viewer.
 */
export default function ScaleBar({ viewer, wcsParams }: ScaleBarProps) {
  const [barWidthPx, setBarWidthPx] = useState(0);
  const [label, setLabel] = useState("");
  const [pixelCount, setPixelCount] = useState(0);

  // Pixel scale in arcseconds per image pixel (from CD matrix)
  const pixelScaleArcsec =
    Math.sqrt(wcsParams.cd1_1 ** 2 + wcsParams.cd2_1 ** 2) * 3600;

  const updateScale = useCallback(() => {
    if (!viewer?.viewport) return;

    // Get image-pixels-per-screen-pixel at current zoom
    // OpenSeadragon zoom = viewport width / image width at zoom 1
    const zoom = viewer.viewport.getZoom(true);
    const containerWidth = viewer.viewport.getContainerSize().x;
    const imageWidth = wcsParams.naxis1;

    // Image pixels visible across the container width
    const imagePixelsAcrossScreen = imageWidth / zoom;

    // Screen pixels per image pixel
    const screenPixelsPerImagePixel = containerWidth / imagePixelsAcrossScreen;

    // Arcseconds per screen pixel
    const arcsecPerScreenPixel = pixelScaleArcsec / screenPixelsPerImagePixel;

    // Max arcseconds that fit in MAX_BAR_WIDTH_PX
    const maxArcsec = arcsecPerScreenPixel * MAX_BAR_WIDTH_PX;

    // Find the largest "nice" value that fits
    let chosenArcsec = NICE_ARCSEC_VALUES[0];
    for (const val of NICE_ARCSEC_VALUES) {
      if (val <= maxArcsec) {
        chosenArcsec = val;
      } else {
        break;
      }
    }

    // Compute bar width in screen pixels
    const barPx = chosenArcsec / arcsecPerScreenPixel;
    const imagePixels = Math.round(chosenArcsec / pixelScaleArcsec);

    setBarWidthPx(Math.round(barPx));
    setLabel(formatAngularSize(chosenArcsec));
    setPixelCount(imagePixels);
  }, [viewer, wcsParams.naxis1, pixelScaleArcsec]);

  // Listen to zoom/pan events
  useEffect(() => {
    if (!viewer) return;

    const handler = () => updateScale();
    viewer.addHandler("zoom", handler);
    viewer.addHandler("open", handler);
    viewer.addHandler("resize", handler);

    // Initial update
    updateScale();

    return () => {
      viewer.removeHandler("zoom", handler);
      viewer.removeHandler("open", handler);
      viewer.removeHandler("resize", handler);
    };
  }, [viewer, updateScale]);

  if (barWidthPx <= 0) return null;

  return (
    <div className="absolute bottom-10 right-4 flex flex-col items-end gap-0.5 z-10">
      <div
        className="h-0.5 bg-white/80"
        style={{ width: `${barWidthPx}px` }}
      />
      <div className="text-xs text-zinc-400 font-mono">
        {label}
        <span className="text-zinc-600 ml-2">{pixelCount}px</span>
      </div>
    </div>
  );
}
