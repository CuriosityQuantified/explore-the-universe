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
