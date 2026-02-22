"use client";

import { useState, useCallback } from "react";

/** CSS filter adjustment values applied to the OpenSeadragon canvas. */
export interface ImageAdjustmentValues {
  brightness: number;
  contrast: number;
  gamma: number;
  invert: boolean;
}

const DEFAULTS: ImageAdjustmentValues = {
  brightness: 1.0,
  contrast: 1.0,
  gamma: 1.0,
  invert: false,
};

interface ImageAdjustmentsProps {
  onAdjustmentChange: (adjustments: ImageAdjustmentValues) => void;
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * Collapsible panel with image adjustment controls.
 *
 * Provides brightness (0.5-2.0), contrast (0.5-2.0), gamma (0.1-3.0),
 * and invert toggle. Reset button restores all values to defaults.
 *
 * The parent applies adjustments via CSS filters on the OpenSeadragon canvas:
 *   brightness(v), contrast(v), invert(0|1)
 *
 * Gamma approximation: since CSS `filter` lacks a native gamma function,
 * we approximate gamma by combining a brightness factor derived from the
 * gamma value: gammaFactor = pow(0.5, 1/gamma - 1). This shifts the
 * midtones similarly to a true gamma curve. It is NOT a true per-pixel
 * power-law transform -- that would require WebGL or canvas pixel
 * manipulation. Acceptable for Phase 3 visual adjustment.
 */
export default function ImageAdjustments({
  onAdjustmentChange,
  isOpen,
  onToggle,
}: ImageAdjustmentsProps) {
  const [adjustments, setAdjustments] = useState<ImageAdjustmentValues>(DEFAULTS);

  const updateAdjustment = useCallback(
    (key: keyof ImageAdjustmentValues, value: number | boolean) => {
      setAdjustments((prev) => {
        const next = { ...prev, [key]: value };
        onAdjustmentChange(next);
        return next;
      });
    },
    [onAdjustmentChange],
  );

  const handleReset = useCallback(() => {
    setAdjustments(DEFAULTS);
    onAdjustmentChange(DEFAULTS);
  }, [onAdjustmentChange]);

  if (!isOpen) return null;

  const isDefault =
    adjustments.brightness === DEFAULTS.brightness &&
    adjustments.contrast === DEFAULTS.contrast &&
    adjustments.gamma === DEFAULTS.gamma &&
    adjustments.invert === DEFAULTS.invert;

  return (
    <div className="absolute top-4 left-16 w-56 bg-zinc-900/90 backdrop-blur-sm border border-zinc-700/50 rounded-lg z-20 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700/50">
        <h3 className="text-xs font-semibold text-zinc-200">
          Image Adjustments
        </h3>
        <button
          onClick={onToggle}
          className="w-5 h-5 flex items-center justify-center rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
          title="Close adjustments"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M2 2 L8 8" />
            <path d="M8 2 L2 8" />
          </svg>
        </button>
      </div>

      {/* Sliders */}
      <div className="px-3 py-2 space-y-3">
        <SliderControl
          label="Brightness"
          value={adjustments.brightness}
          min={0.5}
          max={2.0}
          step={0.05}
          onChange={(v) => updateAdjustment("brightness", v)}
        />
        <SliderControl
          label="Contrast"
          value={adjustments.contrast}
          min={0.5}
          max={2.0}
          step={0.05}
          onChange={(v) => updateAdjustment("contrast", v)}
        />
        <SliderControl
          label="Gamma"
          value={adjustments.gamma}
          min={0.1}
          max={3.0}
          step={0.05}
          onChange={(v) => updateAdjustment("gamma", v)}
        />

        {/* Invert toggle */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-400">Invert</span>
          <button
            onClick={() => updateAdjustment("invert", !adjustments.invert)}
            className={`w-8 h-4 rounded-full relative transition-colors ${
              adjustments.invert ? "bg-cyan-600" : "bg-zinc-700"
            }`}
            title="Toggle invert"
          >
            <span
              className={`block w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform ${
                adjustments.invert ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        {/* Reset button */}
        <button
          onClick={handleReset}
          disabled={isDefault}
          className={`w-full py-1 rounded text-xs transition-colors ${
            isDefault
              ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600 hover:text-white"
          }`}
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}

function SliderControl({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400">{label}</span>
        <span className="text-xs text-zinc-500 font-mono w-10 text-right">
          {value.toFixed(2)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 bg-zinc-700 rounded-full appearance-none cursor-pointer accent-cyan-500 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:appearance-none"
      />
    </div>
  );
}

/**
 * Build CSS filter string from adjustment values.
 *
 * Applied by the parent to the OpenSeadragon canvas element via
 * canvas.style.filter. Called from ViewerClient on every adjustment change.
 *
 * Gamma approximation: CSS filter lacks a native gamma function. We approximate
 * gamma by adjusting brightness with a factor derived from the gamma value:
 *   gammaFactor = pow(0.5, 1/gamma - 1)
 * This shifts midtones similarly to a true gamma curve for gamma values near 1.0.
 * At extreme gamma values the approximation diverges from a true power-law.
 * A proper implementation would require WebGL or per-pixel canvas manipulation.
 */
export function buildCssFilter(adjustments: ImageAdjustmentValues): string {
  const gammaFactor = Math.pow(0.5, 1.0 / adjustments.gamma - 1.0);
  const effectiveBrightness = adjustments.brightness * gammaFactor;

  const parts: string[] = [
    `brightness(${effectiveBrightness.toFixed(3)})`,
    `contrast(${adjustments.contrast.toFixed(3)})`,
  ];

  if (adjustments.invert) {
    parts.push("invert(1)");
  }

  return parts.join(" ");
}
