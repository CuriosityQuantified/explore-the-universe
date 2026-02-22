"use client";

import { useState } from "react";
import type { ObservationDetail, TileMetadata } from "@/types/observation";

interface ObservationInfoProps {
  observation: ObservationDetail;
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * Collapsible sidebar panel displaying observation provenance metadata.
 *
 * Shows telescope, instrument, filters, exposure time, observation ID,
 * pipeline status, pointing RA/Dec, and tile metadata (image dimensions,
 * tile count, zoom levels) when available.
 *
 * Positioned on the right side of the viewer, overlaying the image.
 * Dark semi-transparent background with light text.
 */
export default function ObservationInfo({
  observation,
  isOpen,
  onToggle,
}: ObservationInfoProps) {
  if (!isOpen) return null;

  const formatExposureTime = (seconds: number | null): string => {
    if (seconds === null) return "N/A";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)} min`;
    return `${(seconds / 3600).toFixed(2)} hr`;
  };

  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  const formatRaDec = (
    ra: number | null,
    dec: number | null,
  ): string => {
    if (ra === null || dec === null) return "N/A";
    const decSign = dec >= 0 ? "+" : "";
    return `${ra.toFixed(4)}, ${decSign}${dec.toFixed(4)}`;
  };

  return (
    <div className="absolute top-0 right-0 bottom-0 w-72 bg-zinc-900/90 backdrop-blur-sm border-l border-zinc-700/50 z-20 overflow-y-auto">
      {/* Header with close button */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700/50">
        <h2 className="text-sm font-semibold text-zinc-200">
          Observation Info
        </h2>
        <button
          onClick={onToggle}
          className="w-6 h-6 flex items-center justify-center rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
          title="Close info panel"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M2 2 L10 10" />
            <path d="M10 2 L2 10" />
          </svg>
        </button>
      </div>

      {/* Provenance metadata */}
      <div className="px-4 py-3 space-y-3">
        <InfoSection title="Identification">
          <InfoRow label="Obs ID" value={observation.archive_observation_id} mono />
          <InfoRow label="UUID" value={observation.observation_uuid.slice(0, 8) + "..."} mono />
          <InfoRow label="Status" value={observation.pipeline_status} />
        </InfoSection>

        <InfoSection title="Instrument">
          <InfoRow label="Telescope" value={observation.telescope_name} />
          <InfoRow label="Instrument" value={observation.instrument_name} />
          <InfoRow
            label="Filters"
            value={
              observation.spectral_filters
                ? observation.spectral_filters.join(", ")
                : "N/A"
            }
          />
          <InfoRow
            label="Exposure"
            value={formatExposureTime(observation.total_exposure_seconds)}
          />
        </InfoSection>

        <InfoSection title="Pointing">
          <InfoRow
            label="RA/Dec"
            value={formatRaDec(
              observation.pointing_ra_degrees,
              observation.pointing_dec_degrees,
            )}
            mono
          />
        </InfoSection>

        <InfoSection title="Timing">
          <InfoRow
            label="Ingested"
            value={formatDate(observation.ingested_at)}
          />
        </InfoSection>

        {observation.tile_metadata && (
          <TileInfoSection tileMetadata={observation.tile_metadata} />
        )}
      </div>
    </div>
  );
}

function InfoSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1.5">
        {title}
      </h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2 text-xs">
      <span className="text-zinc-500 shrink-0">{label}</span>
      <span
        className={`text-zinc-300 text-right break-all ${mono ? "font-mono" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function TileInfoSection({
  tileMetadata,
}: {
  tileMetadata: TileMetadata;
}) {
  return (
    <InfoSection title="Tile Data">
      <InfoRow
        label="Dimensions"
        value={`${tileMetadata.image_width_pixels} x ${tileMetadata.image_height_pixels} px`}
        mono
      />
      <InfoRow
        label="Tiles"
        value={String(tileMetadata.tile_count)}
        mono
      />
      <InfoRow
        label="Zoom levels"
        value={String(tileMetadata.max_zoom_level)}
        mono
      />
      <InfoRow
        label="Tile size"
        value={`${tileMetadata.tile_size_pixels}px`}
        mono
      />
      <InfoRow
        label="Files processed"
        value={String(tileMetadata.files_processed)}
        mono
      />
    </InfoSection>
  );
}
