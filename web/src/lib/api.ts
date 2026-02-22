/**
 * API client functions for the sky viewer.
 *
 * Fetches observation data and WCS parameters from the FastAPI backend
 * (api/routers/tiles.py). Also provides the tile URL base for
 * OpenSeadragon's DZI tile source configuration.
 *
 * Uses standard fetch() -- no external HTTP library needed.
 */

import type { ObservationDetail, WcsParams } from "@/types/observation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
