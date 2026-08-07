/**
 * API client functions for the sky viewer.
 *
 * Fetches observation data and WCS parameters from the FastAPI backend
 * (api/routers/tiles.py). Also provides the tile URL base for
 * OpenSeadragon's DZI tile source configuration.
 *
 * Uses standard fetch() -- no external HTTP library needed.
 */

import type { ObservationDetail, ObservationSummary, WcsParams } from "@/types/observation";
import type { ObjectDetail } from "@/types/object";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch the list of all ingested observations with pipeline status and counts.
 *
 * Calls GET /api/observations which returns all observations ordered by
 * ingestion time (newest first), with object/classified/anomaly counts and
 * the processing step timeline.
 *
 * @returns Array of ObservationSummary (empty array if none ingested)
 * @throws Error if the response is not ok
 */
export async function fetchObservations(): Promise<ObservationSummary[]> {
  const response = await fetch(`${API_BASE}/api/observations`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to fetch observations: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch observation detail (provenance + tile metadata) from the backend.
 *
 * Calls GET /api/tiles/{uuid} which returns the Observation record
 * joined with the completed generate_tiles ProcessingStep metadata.
 *
 * @param uuid - Observation UUID (hex string, e.g. "a1b2c3d4...")
 * @returns ObservationDetail with provenance fields and tile_metadata (or null)
 * @throws Error if the response is not ok (404 for missing observation, etc.)
 */
export async function fetchObservation(
  uuid: string,
): Promise<ObservationDetail> {
  const response = await fetch(`${API_BASE}/api/tiles/${uuid}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to fetch observation: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch WCS parameters for client-side pixel-to-sky coordinate conversion.
 *
 * Calls GET /api/tiles/{uuid}/wcs which extracts CRPIX, CRVAL, CD matrix,
 * CTYPE, and NAXIS from the FITS file stored in MinIO.
 *
 * @param uuid - Observation UUID (hex string)
 * @returns WcsParams with all 12 WCS fields needed for TAN gnomonic deprojection
 * @throws Error if the response is not ok (404 if no FITS files found)
 */
export async function fetchWcsParams(uuid: string): Promise<WcsParams> {
  const response = await fetch(`${API_BASE}/api/tiles/${uuid}/wcs`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to fetch WCS params: ${response.status}`);
  }
  return response.json();
}

/**
 * Get the tile URL base for OpenSeadragon's DZI tile source.
 *
 * OpenSeadragon appends {level}/{col}_{row}.jpg to this base URL
 * to construct individual tile requests. The FastAPI proxy at
 * /api/tiles/{uuid}/{level}/{col}_{row}.jpg streams tiles from MinIO.
 *
 * @param uuid - Observation UUID (hex string)
 * @returns Base URL string for the tile source Url property
 */
export function getTileUrl(uuid: string): string {
  return `${API_BASE}/api/tiles/${uuid}/`;
}

/**
 * Fetch full detail for a single astronomical object.
 *
 * Calls GET /api/objects/{uuid} which returns the object record including
 * sky coordinates, classification, cross-matches, physical properties,
 * segmentation mask RLE, and a signed cutout URL.
 *
 * @param uuid - Object UUID
 * @returns ObjectDetail with all aggregated data for the object
 * @throws Error with message "NOT_FOUND" for 404, or a description for other errors
 */
export async function fetchObjectDetail(uuid: string): Promise<ObjectDetail> {
  const response = await fetch(`${API_BASE}/api/objects/${uuid}`);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("NOT_FOUND");
    }
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to fetch object: ${response.status}`);
  }
  return response.json();
}
