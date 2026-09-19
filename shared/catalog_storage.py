"""S3 access for the managed survey bucket, independent of existing JWST data."""
from functools import lru_cache

import boto3
from botocore.config import Config

from shared.config import settings


@lru_cache(maxsize=1)
def get_catalog_s3_client():
    if not settings.catalog_s3_bucket:
        raise RuntimeError("CATALOG_S3_BUCKET is not configured")
    return boto3.client(
        "s3", endpoint_url=settings.catalog_s3_endpoint_url,
        aws_access_key_id=settings.catalog_s3_access_key,
        aws_secret_access_key=settings.catalog_s3_secret_key,
        region_name=settings.catalog_s3_region,
        config=Config(signature_version="s3v4", connect_timeout=10, read_timeout=30,
                      retries={"max_attempts": 3},
                      s3={"addressing_style": settings.catalog_s3_url_style}),
    )


def is_catalog_cutout(prefix: str | None) -> bool:
    return bool(prefix and prefix.startswith("catalog/"))
