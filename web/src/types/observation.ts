/**
 * TypeScript interfaces matching the backend response models in
 * api/routers/tiles.py. These are the contract between the FastAPI
 * backend and the Next.js frontend for observation data, WCS parameters,
 * and tile metadata.
 */

/** WCS header parameters for client-side pixel-to-sky coordinate conversion.
 *
 * Matches WcsParamsResponse from api/routers/tiles.py.
 * Used by lib/wcs.ts TAN gnomonic deprojection to convert OpenSeadragon
 * image pixel coordinates to RA/Dec sky coordinates.
 */
export interface WcsParams {
  crpix1: number;
  crpix2: number;
  crval1: number;
  crval2: number;
  cd1_1: number;
  cd1_2: number;
  cd2_1: number;
  cd2_2: number;
  ctype1: string;
  ctype2: string;
  naxis1: number;
  naxis2: number;
}

/** Tile generation metadata from the generate_tiles processing step.
 *
 * Matches TileMetadataResponse from api/routers/tiles.py.
 * Populated from ProcessingStep.step_output_metadata where
 * step_name == "generate_tiles" and step_status == "completed".
 */
export interface TileMetadata {
  tile_count: number;
  max_zoom_level: number;
  tile_size_pixels: number;
  dzi_s3_key: string;
  normalization_vmin: number;
  normalization_vmax: number;
  image_width_pixels: number;
  image_height_pixels: number;
  total_bytes_uploaded: number;
  files_processed: number;
}

/** Observation provenance and tile metadata for the info panel.
 *
 * Matches ObservationDetailResponse from api/routers/tiles.py.
 * Contains the full observation record plus tile metadata from the
 * completed generate_tiles processing step (or null if tiling is
 * not yet complete).
 */
export interface ObservationDetail {
  observation_uuid: string;
  archive_observation_id: string;
  telescope_name: string;
  instrument_name: string;
  spectral_filters: string[] | null;
  total_exposure_seconds: number | null;
  pointing_ra_degrees: number | null;
  pointing_dec_degrees: number | null;
  pipeline_status: string;
  ingested_at: string;
  tile_metadata: TileMetadata | null;
}
