/**
 * TypeScript interfaces for the search API endpoints.
 * Matches api/routers/objects.py ObjectSearchResponse and NameSearchResponse.
 */

export interface ObjectSearchItem {
  object_uuid: string;
  sky_coordinate_ra_degrees: number;
  sky_coordinate_dec_degrees: number;
  classified_object_type: string | null;
  catalog_object_name: string | null;
  is_anomaly_flagged: boolean;
  cutout_thumbnail_url: string | null;
}

export interface NameSearchResult {
  results: ObjectSearchItem[];
  resolved_ra: number | null;
  resolved_dec: number | null;
  simbad_name: string | null;
  /** Total matching objects (from X-Total-Count response header). */
  total: number;
}

/**
 * Request body for POST /api/objects/search structured query.
 * All fields are optional; omitting a field skips that filter.
 */
export interface StructuredSearchFilters {
  type?: string[];
  magnitude_min?: number;
  magnitude_max?: number;
  redshift_min?: number;
  redshift_max?: number;
  is_anomaly?: boolean;
  observation_uuid?: string;
  sort_by?: "magnitude" | "type" | "angular_separation";
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

/**
 * Response from POST /api/objects/search.
 * total_count is the unsliced count for pagination.
 */
export interface StructuredSearchResult {
  results: ObjectSearchItem[];
  total_count: number;
}
