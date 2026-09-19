"""Offline regression tests for real catalog parsing and bounded imagery imports."""
import io
from unittest.mock import patch

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from pipeline.catalog import coordinate, normalize_name, parse_catalog, diverse_order, field_of_view
from pipeline.catalog_import import identity, make_assets, import_image, prepare_images


def test_coordinate_rollover_and_negative_zero():
    assert coordinate("-00:30:00") == -0.5
    assert coordinate("+07:12:60.0") == pytest.approx(7 + 13 / 60)
    assert coordinate("12:00:00", ra=True) == 180
    for value in ("91:00:00", "00:61:00", "nan:00:00"):
        with pytest.raises(ValueError):
            coordinate(value)


def target():
    csv = "Name;Type;RA;Dec;M;Common names;MajAx;V-Mag\nNGC0224;G;00:42:44.3;+41:16:09;031;Andromeda Galaxy;178;3.44\nNGC0001;Dup;01:00:00;+10:00:00;;;;\nNGC0002;NonEx;01:00:00;+10:00:00;;;;\n"
    records = parse_catalog(csv)
    assert len(records) == 1
    return records[0]


def test_catalog_aliases_and_provenance():
    t = target()
    assert t["name"] == "M31"
    assert t["type"] == "galaxy"
    assert t["properties"]["aliases"] == ["andromedagalaxy", "m31", "ngc224"]
    assert normalize_name("NGC 00224") == "ngc224"
    assert t["properties"]["catalog_license"].endswith("/by-sa/4.0/")
    assert identity(t) == identity(dict(t))
    assert field_of_view(t) == pytest.approx(4.45)


def test_diversity_interleaves_sky_sectors():
    records = [dict(target(), id=str(i), messier=False, dec=-60 if i < 3 else 60) for i in range(6)]
    ordered = diverse_order(records)
    assert [t["dec"] for t in ordered[:4]] == [-60, 60, -60, 60]
    assert {t["id"] for t in ordered} == {str(i) for i in range(6)}


def survey_fits():
    w = WCS(naxis=2)
    w.wcs.crpix = [256.5, 256.5]
    w.wcs.crval = [10.68, 41.27]
    w.wcs.cdelt = [-0.001, 0.001]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    output = io.BytesIO()
    fits.PrimaryHDU(np.random.default_rng(42).normal(100, 10, (512, 512)), header=w.to_header()).writeto(output)
    return output.getvalue()


def test_assets_include_original_fits_and_valid_tile_pyramid():
    data = survey_fits()
    assets, metadata = make_assets(target(), data)
    assert metadata["tile_count"] == 13
    assert metadata["total_bytes_uploaded"] == sum(len(body) for _, body, _ in assets)
    assert next(body for key, body, _ in assets if key.endswith("cutout.fits")) == data
    for key, body, content_type in assets:
        if content_type == "image/jpeg" and "/9/" in key:
            assert Image.open(io.BytesIO(body)).size == (257, 257)


def test_budget_exhaustion_does_not_upload_or_commit():
    with patch("pipeline.catalog_import.fetch_bytes", return_value=survey_fits()), patch("pipeline.catalog_import.get_catalog_s3_client") as storage, patch("pipeline.catalog_import.SessionLocal") as db:
        with pytest.raises(OverflowError):
            import_image(target(), remaining_bytes=1)
        storage.assert_not_called()
        db.assert_not_called()


def test_invalid_image_rejected():
    with pytest.raises(Exception):
        prepare_images(b"upstream error page")


def test_display_orientation_matches_viewer_fits_y_flip():
    data = survey_fits()
    with fits.open(io.BytesIO(data)) as hdus:
        hdus[0].data[:] = np.arange(512)[:, None]
        buffer = io.BytesIO()
        hdus.writeto(buffer)
    image, _ = prepare_images(buffer.getvalue())
    pixels = np.asarray(image)
    assert pixels[0, 256] > pixels[-1, 256]
