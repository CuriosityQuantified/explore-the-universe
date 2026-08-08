/**
 * TypeScript interfaces for the object detail API endpoint.
 * Matches api/routers/objects.py ObjectDetailResponse and related models.
 */

export interface CrossMatchDetail {
  match_uuid: string;
  catalog_name: string;
  catalog_source_id: string;
  angular_separation_arcseconds: number;
  match_probability_score: number | null;
  external_url: string | null;
}

export interface ClassificationDetail {
  classification_uuid: string;
  predicted_object_type: string;
  classification_confidence_score: number;
  ml_model_version: string;
  classified_at: string | null;
  is_anomaly_flagged: boolean;
  anomaly_score: number | null;
  anomaly_explanation: string | null;
}

export interface CocoRle {
  size: [number, number];
  counts: string;
}

export interface ObjectDetail {
  object_uuid: string;
  source_observation_uuid: string;
  sky_coordinate_ra_degrees: number;
  sky_coordinate_dec_degrees: number;
  bounding_box_pixels: Record<string, unknown> | null;
  classified_object_type: string | null;
  catalog_object_name: string | null;
  catalog_magnitude: number | null;
  catalog_redshift: number | null;
  is_anomaly_flagged: boolean;
  physical_properties: Record<string, number | string | null> | null;
  segmentation_mask_rle: CocoRle | null;
  cutout_url: string | null;
  cross_matches: CrossMatchDetail[];
  latest_classification: ClassificationDetail | null;
}

export interface GraphNeighborNode {
  uuid: string;
  type?: string | null;
  thumbnail_url?: string | null;
}

export interface GraphCatalogEntry {
  catalog: string;
  source_id: string;
}

export interface GraphNeighbors {
  in_graph: boolean;
  contains_children: GraphNeighborNode[];
  contained_by: GraphNeighborNode[];
  catalog_entries: GraphCatalogEntry[];
}
