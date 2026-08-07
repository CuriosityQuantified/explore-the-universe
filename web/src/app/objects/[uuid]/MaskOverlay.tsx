"use client";

import { useMemo } from "react";
import type { CocoRle } from "@/types/object";

/**
 * Decode COCO compressed RLE to a flat column-major Uint8Array.
 * Encoding: each value uses variable-length 5-bit chunks; chars in [48,111].
 * The 6th bit (value 32) signals continuation. Mask stored column-major (F-order).
 */
function decompressCocoRle(counts: string, h: number, w: number): Uint8Array {
  const mask = new Uint8Array(h * w);
  let p = 0;
  let bit = 0;
  let i = 0;
  while (i < counts.length) {
    let x = 0;
    let k = 0;
    let more = true;
    while (more) {
      const c = counts.charCodeAt(i++) - 48;
      more = (c & 32) !== 0;
      x |= (c & 31) << (5 * k++);
    }
    if (bit === 1) {
      const end = Math.min(p + x, h * w);
      mask.fill(1, p, end);
    }
    p += x;
    bit ^= 1;
  }
  return mask;
}

/**
 * Convert column-major COCO mask to SVG path string (column-run rectangles).
 * Each column's runs of set pixels become 1-wide rectangles.
 * fill-rule: evenodd on the parent <svg> gives correct boundary semantics.
 */
function maskToSvgPath(mask: Uint8Array, h: number, w: number): string {
  const parts: string[] = [];
  for (let c = 0; c < w; c++) {
    let runStart = -1;
    for (let r = 0; r <= h; r++) {
      const val = r < h ? mask[c * h + r] : 0;
      if (val && runStart === -1) {
        runStart = r;
      } else if (!val && runStart !== -1) {
        parts.push(`M${c},${runStart}h1v${r - runStart}h-1Z`);
        runStart = -1;
      }
    }
  }
  return parts.join(" ");
}

interface MaskOverlayProps {
  rle: CocoRle;
}

export function MaskOverlay({ rle }: MaskOverlayProps) {
  const [h, w] = rle.size;

  const svgPath = useMemo(() => {
    const mask = decompressCocoRle(rle.counts, h, w);
    return maskToSvgPath(mask, h, w);
  }, [rle.counts, h, w]);

  if (!svgPath) return null;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        opacity: 0.3,
      }}
      fillRule="evenodd"
      aria-hidden="true"
    >
      <path d={svgPath} fill="#8040ff" />
    </svg>
  );
}
