export type CatalogSort = "name" | "type" | "magnitude" | "redshift" | "ra" | "dec";

export interface CatalogFilters {
  q?: string;
  type?: string;
  has_image?: boolean;
  hemisphere?: "north" | "south";
  magnitude_min?: number;
  magnitude_max?: number;
  sort_by?: CatalogSort;
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface CatalogObject {
  object_uuid: string;
  catalog_object_name: string | null;
  classified_object_type: string | null;
  catalog_magnitude: number | null;
  catalog_redshift: number | null;
  sky_coordinate_ra_degrees: number;
  sky_coordinate_dec_degrees: number;
  has_image: boolean;
  constellation: string | null;
}

export interface CatalogPage {
  results: CatalogObject[];
  total_count: number;
  limit: number;
  offset: number;
}
