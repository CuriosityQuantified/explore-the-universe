"""Tile serving API endpoints for the sky viewer.

GET /api/tiles/{observation_uuid}/{level}/{col}_{row}.jpg -- Stream tile JPEG from MinIO
GET /api/tiles/{observation_uuid}/wcs -- Extract WCS parameters from FITS for client-side projection
GET /api/tiles/{observation_uuid} -- Observation detail with provenance and tile metadata
"""

import logging
import os
import tempfile

from astropy.io import fits
from astropy.wcs import WCS
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.config import settings
from shared.models import Observation, ProcessingStep, StepStatus
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


# --- Response Models ---


class WcsParamsResponse(BaseModel):
    """WCS header parameters for client-side pixel-to-sky coordinate conversion."""

    crpix1: float
    crpix2: float
    crval1: float
    crval2: float
    cd1_1: float
    cd1_2: float
    cd2_1: float
    cd2_2: float
    ctype1: str
    ctype2: str
    naxis1: int
    naxis2: int


class TileMetadataResponse(BaseModel):
    """Tile generation metadata from the generate_tiles processing step."""

    tile_count: int
    max_zoom_level: int
    tile_size_pixels: int
    dzi_s3_key: str
    normalization_vmin: float
    normalization_vmax: float
    image_width_pixels: int
    image_height_pixels: int
    total_bytes_uploaded: int
    files_processed: int


class ObservationDetailResponse(BaseModel):
    """Observation provenance and tile metadata for the info panel."""

    observation_uuid: str
    archive_observation_id: str
    telescope_name: str
    instrument_name: str
    spectral_filters: list[str] | None
    total_exposure_seconds: float | None
    pointing_ra_degrees: float | None
    pointing_dec_degrees: float | None
    pipeline_status: str
    ingested_at: str
    tile_metadata: TileMetadataResponse | None


# --- Helper Functions ---


def _find_sci_extension(hdul):
    """Find the SCI extension in a FITS HDU list.

    Same logic as pipeline/tasks/tile.py _find_sci_extension: checks for named
    'SCI' extension first (JWST MEF standard), falls back to primary HDU, then
    scans all extensions.

    Args:
        hdul: An opened astropy FITS HDU list.

    Returns:
        The HDU containing science image data.

    Raises:
        ValueError: If no HDU with image data can be found.
    """
    try:
        sci_hdu = hdul["SCI"]
        if sci_hdu.header.get("NAXIS", 0) > 0:
            return sci_hdu
    except KeyError:
        pass

    primary_hdu = hdul[0]
    if primary_hdu.header.get("NAXIS", 0) > 0:
        logger.warning(
            "Using primary HDU (hdul[0]) instead of named SCI extension"
        )
        return primary_hdu

    for index, hdu in enumerate(hdul):
        if hdu.header.get("NAXIS", 0) > 0:
            logger.warning(
                "Using extension %d (%s) as fallback", index, hdu.name
            )
            return hdu

    raise ValueError("No HDU with image data (NAXIS > 0) found in FITS file")


# --- Endpoints ---


@router.get("/{observation_uuid}/{level}/{col}_{row}.jpg")
def get_tile(observation_uuid: str, level: int, col: int, row: int):
    """Stream a tile JPEG from MinIO.

    Proxies tile requests to MinIO to avoid CORS issues with direct browser
    access. Returns immutable cache headers since tiles never change once
    generated.

    S3 key structure: {observation_uuid}/tiles/{level}/{col}_{row}.jpg
    (matches pipeline/tasks/tile.py _upload_tiles_to_minio)
    """
    s3_key = f"{observation_uuid}/tiles/{level}/{col}_{row}.jpg"
    s3_client = get_s3_client()

    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_tiles, Key=s3_key
        )
    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        if error_code in ("NoSuchKey", "404"):
            raise HTTPException(
                status_code=404,
                detail=f"Tile not found: {level}/{col}_{row}.jpg",
            )
        raise

    return StreamingResponse(
        response["Body"],
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/{observation_uuid}/wcs", response_model=WcsParamsResponse)
def get_wcs_params(observation_uuid: str):
    """Extract WCS parameters from the primary FITS file for client-side projection.

    Downloads the first FITS file for this observation from MinIO, opens it
    with astropy, extracts the WCS header keywords (CRPIX, CRVAL, CD matrix,
    CTYPE, NAXIS), and returns them as JSON for the frontend TAN gnomonic
    deprojection.

    CD matrix fallback: If CD keywords are missing (older FITS files), falls
    back to CDELT1/CDELT2 for the diagonal elements.
    """
    s3_client = get_s3_client()

    # Find the first FITS file in MinIO under this observation's prefix
    response = s3_client.list_objects_v2(
        Bucket=settings.s3_bucket_fits_raw,
        Prefix=f"{observation_uuid}/",
        MaxKeys=1,
    )
    contents = response.get("Contents", [])
    if not contents:
        raise HTTPException(
            status_code=404,
            detail=f"No FITS files found for observation {observation_uuid}",
        )

    fits_s3_key = contents[0]["Key"]

    # Download to temp file and extract WCS header keywords
    temp_fd, temp_path = tempfile.mkstemp(suffix=".fits")
    os.close(temp_fd)

    try:
        s3_client.download_file(
            settings.s3_bucket_fits_raw, fits_s3_key, temp_path
        )

        with fits.open(temp_path, memmap=True, mode="denywrite") as hdul:
            sci_hdu = _find_sci_extension(hdul)
            science_header = sci_hdu.header

            wcs_obj = WCS(science_header)
            if wcs_obj.naxis > 2:
                wcs_obj = wcs_obj.celestial

            wcs_header = wcs_obj.to_header()

            # Extract CD matrix with CDELT fallback for older FITS files
            cd1_1 = float(
                wcs_header.get("CD1_1", wcs_header.get("CDELT1", 0))
            )
            cd1_2 = float(wcs_header.get("CD1_2", 0))
            cd2_1 = float(wcs_header.get("CD2_1", 0))
            cd2_2 = float(
                wcs_header.get("CD2_2", wcs_header.get("CDELT2", 0))
            )

            return WcsParamsResponse(
                crpix1=float(wcs_header.get("CRPIX1", 0)),
                crpix2=float(wcs_header.get("CRPIX2", 0)),
                crval1=float(wcs_header.get("CRVAL1", 0)),
                crval2=float(wcs_header.get("CRVAL2", 0)),
                cd1_1=cd1_1,
                cd1_2=cd1_2,
                cd2_1=cd2_1,
                cd2_2=cd2_2,
                ctype1=str(wcs_header.get("CTYPE1", "")),
                ctype2=str(wcs_header.get("CTYPE2", "")),
                naxis1=int(science_header.get("NAXIS1", 0)),
                naxis2=int(science_header.get("NAXIS2", 0)),
            )

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get(
    "/{observation_uuid}",
    response_model=ObservationDetailResponse,
)
def get_observation_detail(
    observation_uuid: str,
    database_session: Session = Depends(get_database_session),
):
    """Return observation provenance metadata and tile metadata.

    Queries the Observation record for provenance (telescope, instrument,
    filters, exposure, pointing) and the completed generate_tiles
    ProcessingStep for tile metadata (tile count, zoom levels, dimensions).
    """
    observation = (
        database_session.query(Observation)
        .filter(Observation.observation_uuid == observation_uuid)
        .first()
    )

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Observation {observation_uuid} not found",
        )

    # Query the completed generate_tiles step for tile metadata
    tile_step = (
        database_session.query(ProcessingStep)
        .filter(
            ProcessingStep.observation_uuid == observation.observation_uuid,
            ProcessingStep.step_name == "generate_tiles",
            ProcessingStep.step_status == StepStatus.completed,
        )
        .first()
    )

    tile_metadata = None
    if tile_step and tile_step.step_output_metadata:
        tile_metadata = TileMetadataResponse(
            **tile_step.step_output_metadata
        )

    return ObservationDetailResponse(
        observation_uuid=str(observation.observation_uuid),
        archive_observation_id=observation.archive_observation_id,
        telescope_name=observation.telescope_name,
        instrument_name=observation.instrument_name,
        spectral_filters=observation.spectral_filters,
        total_exposure_seconds=observation.total_exposure_seconds,
        pointing_ra_degrees=observation.pointing_ra_degrees,
        pointing_dec_degrees=observation.pointing_dec_degrees,
        pipeline_status=observation.pipeline_status.value,
        ingested_at=observation.ingested_at.isoformat(),
        tile_metadata=tile_metadata,
    )
