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
import type { GraphNeighbors, ObjectDetail } from "@/types/object";
import type { NameSearchResult, ObjectSearchItem } from "@/types/search";

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

/** Throw a descriptive Error from a non-ok API response. */
async function throwApiError(response: Response, label: string): Promise<never> {
  const body = await response.json().catch(() => ({ detail: response.statusText }));
  throw new Error(body.detail || `${label}: ${response.status}`);
}

/** Fetch the list of distinct classified_object_type values from the DB. */
export async function fetchObjectTypes(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/api/objects/types`);
  if (!response.ok) await throwApiError(response, "Failed to fetch object types");
  return response.json();
}

/**
 * Search objects by SIMBAD name. Resolves the name to sky coordinates via
 * SIMBAD, then performs a 5-arcsec cone search against the local catalog.
 *
 * @param name - Astronomical object name (e.g. "NGC 1300")
 * @throws Error with status 503 message when SIMBAD is unreachable
 */
export async function searchByName(
  name: string,
  limit = 50,
  offset = 0,
): Promise<NameSearchResult> {
  const params = new URLSearchParams({ name, limit: String(limit), offset: String(offset) });
  const response = await fetch(`${API_BASE}/api/objects/search?${params}`);
  if (!response.ok) await throwApiError(response, "Name search failed");
  const total = Number(response.headers.get("x-total-count") ?? "0");
  const body: Omit<NameSearchResult, "total"> = await response.json();
  return { ...body, total };
}

/**
 * Cone search: return objects within radius_arcsec of the given RA/Dec.
 *
 * @param ra - Right ascension in degrees
 * @param dec - Declination in degrees
 * @param radiusArcsec - Search radius in arcseconds
 */
export async function searchByCone(
  ra: number,
  dec: number,
  radiusArcsec: number,
  limit = 50,
  offset = 0,
): Promise<{ results: ObjectSearchItem[]; total: number }> {
  const params = new URLSearchParams({
    ra: String(ra),
    dec: String(dec),
    radius_arcsec: String(radiusArcsec),
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`${API_BASE}/api/objects/search?${params}`);
  if (!response.ok) await throwApiError(response, "Cone search failed");
  const total = Number(response.headers.get("x-total-count") ?? "0");
  const results: ObjectSearchItem[] = await response.json();
  return { results, total };
}

/**
 * Filter objects by classified_object_type.
 *
 * @param type - Classified object type string (e.g. "spiral_galaxy")
 */
export async function searchByType(
  type: string,
  limit = 50,
  offset = 0,
): Promise<{ results: ObjectSearchItem[]; total: number }> {
  const params = new URLSearchParams({ type, limit: String(limit), offset: String(offset) });
  const response = await fetch(`${API_BASE}/api/objects/search?${params}`);
  if (!response.ok) await throwApiError(response, "Type search failed");
  const total = Number(response.headers.get("x-total-count") ?? "0");
  const results: ObjectSearchItem[] = await response.json();
  return { results, total };
}

/**
 * Fetch 1-hop knowledge graph neighbors for an astronomical object.
 *
 * Calls GET /api/objects/{uuid}/graph-neighbors which returns CONTAINS
 * children, CONTAINS parents, and SAME_AS catalog entries for the object's
 * Neo4j node.  Returns ``{ in_graph: false }`` when no node exists.
 *
 * @param uuid - Object UUID
 * @returns GraphNeighbors with in_graph flag and neighbor lists
 * @throws Error if the response is not ok
 */
export async function fetchGraphNeighbors(uuid: string): Promise<GraphNeighbors> {
  const response = await fetch(`${API_BASE}/api/objects/${uuid}/graph-neighbors`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
