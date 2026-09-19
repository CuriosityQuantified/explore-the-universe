"""Bounded, resumable OpenNGC + DSS2 import. Run with python -m pipeline.catalog_import.

All named catalog records are indexed first. Real, WCS-bearing survey cutouts
are then added in a sky-diverse order. Each completed target is committed
independently, so rerunning skips completed imagery. No Celery or GPU required.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import math
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch, ZScaleInterval
from astropy.wcs import WCS
from PIL import Image
from sqlalchemy import BigInteger, func, select, text
from sqlalchemy.dialects.postgresql import insert

from api.db.session import SessionLocal, engine
from pipeline.catalog import CATALOG_ROOT, SURVEY, diverse_order, field_of_view, parse_catalog
from shared.catalog_storage import get_catalog_s3_client
from shared.config import settings
from shared.models import AstronomicalObject, Observation, PipelineStatus, ProcessingStep, StepStatus

logger = logging.getLogger(__name__)
NAMESPACE = uuid.UUID("d06332d1-6774-4f56-9eee-5ca9eb977c79")
PIXELS = 512
MAX_DOWNLOAD_BYTES = 4_000_000
LOCK_ID = 731804219


def identity(target: dict) -> tuple[uuid.UUID, uuid.UUID]:
    return (uuid.uuid5(NAMESPACE, "observation:" + target["id"]),
            uuid.uuid5(NAMESPACE, "object:" + target["id"]))


def fetch_bytes(url: str, maximum: int = MAX_DOWNLOAD_BYTES) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ExploreTheUniverse/0.1 (astronomy catalog; bounded research cutouts)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Download exceeded the per-file byte limit")
    return data


def load_targets() -> list[dict]:
    records = {}
    for filename in ("NGC.csv", "addendum.csv"):
        for target in parse_catalog(fetch_bytes(f"{CATALOG_ROOT}/database_files/{filename}", 8_000_000).decode("utf-8-sig")):
            records[target["id"]] = target
    return diverse_order(list(records.values()))


def seed_catalog(targets: list[dict]) -> int:
    """Import genuine published records idempotently, without fabricated detections."""
    with SessionLocal() as session:
        for start in range(0, len(targets), 500):
            observations, objects = [], []
            for target in targets[start:start + 500]:
                obs_id, obj_id = identity(target)
                observations.append(dict(
                    observation_uuid=obs_id, archive_observation_id="OpenNGC:" + target["id"],
                    telescope_name="DSS2", instrument_name="Digitized Sky Survey (red)",
                    spectral_filters=["red"], pointing_ra_degrees=target["ra"],
                    pointing_dec_degrees=target["dec"], pipeline_status=PipelineStatus.pending,
                ))
                objects.append(dict(
                    object_uuid=obj_id, source_observation_uuid=obs_id,
                    sky_coordinate_ra_degrees=target["ra"], sky_coordinate_dec_degrees=target["dec"],
                    classified_object_type=target["type"], classification_source_catalog="OpenNGC",
                    catalog_object_name=target["name"], catalog_magnitude=target["magnitude"],
                    catalog_redshift=target["redshift"], physical_properties=target["properties"],
                    is_anomaly_flagged=False,
                ))
            session.execute(insert(Observation).values(observations).on_conflict_do_nothing())
            session.execute(insert(AstronomicalObject).values(objects).on_conflict_do_nothing())
            session.commit()
    return len(targets)


def prepare_images(data: bytes) -> tuple[Image.Image, dict]:
    """Validate a real 2-D celestial FITS image and stretch it for display."""
    with fits.open(io.BytesIO(data), memmap=False) as hdus:
        hdu = next(h for h in hdus if h.data is not None and h.data.ndim == 2)
        array = np.asarray(hdu.data, dtype=np.float32)
        if array.shape != (PIXELS, PIXELS) or not WCS(hdu.header).has_celestial:
            raise ValueError("Survey response has unexpected dimensions or no celestial WCS")
        finite = array[np.isfinite(array)]
        if finite.size < array.size * 0.5 or np.ptp(finite) == 0:
            raise ValueError("Survey image has no usable coverage")
        vmin, vmax = map(float, ZScaleInterval().get_limits(finite))
        if vmax <= vmin:
            raise ValueError("Survey image has no display contrast")
        normalized = np.clip((np.nan_to_num(array, nan=vmin) - vmin) / (vmax - vmin), 0, 1)
        image = Image.fromarray((AsinhStretch(0.1)(normalized) * 255).astype(np.uint8))
    return image, {"normalization_vmin": vmin, "normalization_vmax": vmax}


def image_bytes(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **({"quality": 85} if fmt == "JPEG" else {}))
    return buffer.getvalue()


def make_assets(target: dict, data: bytes) -> tuple[list[tuple[str, bytes, str]], dict]:
    obs_id, obj_id = identity(target)
    image, normalization = prepare_images(data)
    prefix = f"catalog/{obs_id}/{obj_id}"
    png = image_bytes(image, "PNG")
    assets = [(f"fits/{obs_id}/survey.fits", data, "application/fits"),
              (f"{prefix}/cutout.fits", data, "application/fits"),
              (f"{prefix}/cutout_stretched.png", png, "image/png")]
    max_level = math.ceil(math.log2(PIXELS))
    dzi_key = f"tiles/{obs_id}/image.dzi"
    dzi = (f'<Image TileSize="256" Overlap="1" Format="jpg" xmlns="http://schemas.microsoft.com/deepzoom/2008">'
           f'<Size Width="{PIXELS}" Height="{PIXELS}"/></Image>').encode()
    assets.append((dzi_key, dzi, "application/xml"))
    tile_count = 0
    for level in range(max_level + 1):
        size = math.ceil(PIXELS / 2 ** (max_level - level))
        scaled = image.resize((size, size), Image.Resampling.LANCZOS)
        for row in range(math.ceil(size / 256)):
            for col in range(math.ceil(size / 256)):
                box = (max(0, col * 256 - 1), max(0, row * 256 - 1),
                       min(size, (col + 1) * 256 + 1), min(size, (row + 1) * 256 + 1))
                assets.append((f"tiles/{obs_id}/tiles/{level}/{col}_{row}.jpg",
                               image_bytes(scaled.crop(box), "JPEG"), "image/jpeg"))
                tile_count += 1
    return assets, dict(normalization, tile_count=tile_count, max_zoom_level=max_level,
                        tile_size_pixels=256, dzi_s3_key=dzi_key, image_width_pixels=PIXELS,
                        image_height_pixels=PIXELS, files_processed=1,
                        total_bytes_uploaded=sum(len(content) for _, content, _ in assets))


def import_image(target: dict, remaining_bytes: int) -> int:
    obs_id, obj_id = identity(target)
    params = dict(hips=SURVEY, width=PIXELS, height=PIXELS, fov=field_of_view(target),
                  projection="TAN", coordsys="icrs", ra=target["ra"], dec=target["dec"], format="fits")
    source_url = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits?" + urllib.parse.urlencode(params)
    data = fetch_bytes(source_url)
    assets, tile_metadata = make_assets(target, data)
    total_bytes = tile_metadata["total_bytes_uploaded"]
    if total_bytes > remaining_bytes:
        raise OverflowError("Catalog imagery storage budget reached")
    client = get_catalog_s3_client()
    for key, content, content_type in assets:
        client.put_object(Bucket=settings.catalog_s3_bucket, Key=key, Body=content,
                          ContentType=content_type, Metadata={"catalog": "OpenNGC", "survey": SURVEY})
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        obj, obs = session.get(AstronomicalObject, obj_id), session.get(Observation, obs_id)
        obj.cutout_s3_prefix = f"catalog/{obs_id}/{obj_id}"
        obj.physical_properties = dict(obj.physical_properties, imagery_bytes=total_bytes,
                                      image_source_url=source_url, image_sha256=hashlib.sha256(data).hexdigest(),
                                      field_of_view_degrees=params["fov"], image_status="available")
        obs.pipeline_status = PipelineStatus.completed
        for name, metadata in (("survey_download", {"source_url": source_url, "survey": SURVEY}),
                               ("generate_tiles", tile_metadata)):
            step = session.scalar(select(ProcessingStep).where(ProcessingStep.observation_uuid == obs_id,
                                                              ProcessingStep.step_name == name))
            if step is None:
                step = ProcessingStep(observation_uuid=obs_id, step_name=name)
                session.add(step)
            step.step_status = StepStatus.completed
            step.step_started_at = now
            step.step_completed_at = now
            step.error_message_text = None
            step.step_output_metadata = metadata
        session.commit()
    return total_bytes


def run(max_images: int, max_seconds: int, max_total_bytes: int, metadata_only: bool = False) -> dict:
    # Session-level advisory lock prevents cron overlap or two operators importing at once.
    with engine.connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID}):
            return {"status": "another_import_is_running"}
        try:
            targets = load_targets()
            seed_catalog(targets)
            logger.info("Indexed %d catalog objects", len(targets))
            if metadata_only:
                return {"indexed": len(targets), "images_added": 0}
            client = get_catalog_s3_client()
            client.head_bucket(Bucket=settings.catalog_s3_bucket)
            with SessionLocal() as session:
                completed = set(session.scalars(select(AstronomicalObject.object_uuid).where(
                    AstronomicalObject.classification_source_catalog == "OpenNGC",
                    AstronomicalObject.cutout_s3_prefix.isnot(None))))
                stored = session.scalar(select(func.coalesce(func.sum(
                    AstronomicalObject.physical_properties["imagery_bytes"].astext.cast(BigInteger)), 0)))
            started = time.monotonic()
            added = failures = attempted = 0
            for target in targets:
                if identity(target)[1] in completed:
                    continue
                if attempted >= max_images or time.monotonic() - started >= max_seconds or stored >= max_total_bytes:
                    break
                attempted += 1
                try:
                    stored += import_image(target, max_total_bytes - stored)
                    added += 1
                    logger.info("Imagery %s ready: added=%d total_bytes=%d", target["id"], added, stored)
                except OverflowError:
                    break
                except Exception as exc:
                    failures += 1
                    logger.warning("Imagery %s deferred: %s", target["id"], exc)
                    # An upstream outage must not burn through an entire batch.
                    if failures >= 10:
                        break
                time.sleep(1)  # courteous pacing for the public survey service
            return {"indexed": len(targets), "images_added": added, "images_total": len(completed) + added,
                    "attempted": attempted, "deferred": failures, "stored_bytes": stored}
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-images", type=int, default=250)
    parser.add_argument("--max-seconds", type=int, default=1500)
    parser.add_argument("--max-total-bytes", type=int, default=20_000_000_000)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    if min(args.max_images, args.max_seconds, args.max_total_bytes) <= 0:
        parser.error("Limits must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(run(args.max_images, args.max_seconds, args.max_total_bytes, args.metadata_only)))


if __name__ == "__main__":
    main()
