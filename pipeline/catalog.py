"""Parse the attributed OpenNGC catalog and select diverse survey targets.

Catalog data: Mattia Verga and contributors, CC-BY-SA-4.0.
https://github.com/mattiaverga/OpenNGC
Coordinates are J2000 degrees. Catalog classifications are imported as supplied;
they are not machine-learning predictions or new image detections.
"""
from __future__ import annotations

import csv
import io
import math
import re
from collections import defaultdict, deque

CATALOG_REVISION = "da90466031b0372c896588b85be6016c617e205b"
CATALOG_ROOT = f"https://raw.githubusercontent.com/mattiaverga/OpenNGC/{CATALOG_REVISION}"
CATALOG_URL = "https://github.com/mattiaverga/OpenNGC"
CATALOG_LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
SURVEY = "CDS/P/DSS2/red"
SURVEY_CREDIT = "Digitized Sky Survey 2 (red), STScI; HiPS cutouts provided by CDS, Strasbourg"
TYPE_NAMES = {
    "G": "galaxy", "GPair": "galaxy_pair", "GTrpl": "galaxy_triplet",
    "GGroup": "galaxy_group", "OCl": "open_cluster", "GCl": "globular_cluster",
    "Cl+N": "cluster_with_nebula", "*Ass": "stellar_association", "PN": "planetary_nebula",
    "HII": "hii_region", "DrkN": "dark_nebula", "EmN": "emission_nebula",
    "Neb": "nebula", "RfN": "reflection_nebula", "SNR": "supernova_remnant",
    "*": "star", "**": "double_star", "Nova": "nova", "Other": "other",
}


def normalize_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9]", "", name.casefold())
    return re.sub(r"^(ngc|ic|m)0+(?=\d)", r"\1", value)


def coordinate(value: str, *, ra: bool = False) -> float:
    sign = -1 if value.strip().startswith("-") else 1
    degrees, minutes, seconds = map(float, value.lstrip("+-").split(":"))
    # Published values can round to 60.0 seconds (for example IC3322A).
    if degrees < 0 or not 0 <= minutes < 60 or not 0 <= seconds <= 60:
        raise ValueError("Invalid celestial coordinate")
    result = sign * (degrees + minutes / 60 + seconds / 3600) * (15 if ra else 1)
    if not math.isfinite(result) or (ra and not 0 <= result < 360) or (not ra and not -90 <= result <= 90):
        raise ValueError("Invalid celestial coordinate")
    return result


def number(value: str | None) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def parse_catalog(text: str) -> list[dict]:
    targets = []
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        if row["Type"] in ("Dup", "NonEx") or not row["RA"] or not row["Dec"]:
            continue
        names = [row["Name"]]
        if row.get("M"):
            names.append(f"M{int(row['M'])}")
        for key, prefix in (("NGC", "NGC"), ("IC", "IC")):
            names.extend(prefix + n.strip() for n in row.get(key, "").split(",") if n.strip())
        names.extend(n.strip() for n in row.get("Common names", "").split(",") if n.strip())
        properties = {
            "aliases": sorted({normalize_name(n) for n in names}),
            "names": names, "constellation": row.get("Const"),
            "major_axis_arcmin": number(row.get("MajAx")),
            "minor_axis_arcmin": number(row.get("MinAx")),
            "morphology": row.get("Hubble") or None,
            "catalog": "OpenNGC", "catalog_revision": CATALOG_REVISION,
            "catalog_url": CATALOG_URL, "catalog_license": CATALOG_LICENSE,
            "catalog_credit": "Mattia Verga and OpenNGC contributors",
            "survey": SURVEY, "image_credit": SURVEY_CREDIT,
            "image_kind": "survey cutout, not a new detection",
        }
        targets.append({
            "id": row["Name"], "name": names[1] if row.get("M") else row["Name"],
            "ra": coordinate(row["RA"], ra=True), "dec": coordinate(row["Dec"]),
            "type": TYPE_NAMES.get(row["Type"], "other"),
            "magnitude": number(row.get("V-Mag")) if row.get("V-Mag") else number(row.get("B-Mag")),
            "redshift": number(row.get("Redshift")), "properties": properties,
            "messier": bool(row.get("M")),
        })
    return targets


def diverse_order(targets: list[dict]) -> list[dict]:
    """Messier targets first, then round-robin by sky sector and object type."""
    famous = sorted((t for t in targets if t["messier"]), key=lambda t: int(t["name"][1:]))
    groups = defaultdict(list)
    for target in targets:
        if not target["messier"]:
            band = min(5, int((math.sin(math.radians(target["dec"])) + 1) * 3))
            groups[(band, int(target["ra"] / 30), target["type"])].append(target)
    queues = [deque(sorted(group, key=lambda t: (t["magnitude"] is None, t["magnitude"] or 0, t["id"])))
              for _, group in sorted(groups.items())]
    result = list(famous)
    while queues:
        for queue in queues:
            result.append(queue.popleft())
        queues = [q for q in queues if q]
    return result


def field_of_view(target: dict) -> float:
    return max(0.1, min(6.0, (target["properties"].get("major_axis_arcmin") or 3) * 1.5 / 60))
