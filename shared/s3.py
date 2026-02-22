"""Reusable S3 client singleton for MinIO access.

Provides a lazy-initialized boto3 S3 client configured from application
settings. All pipeline modules should import get_s3_client() from here
rather than creating their own boto3 clients.
"""

import boto3

from shared.config import settings

_s3_client = None


def get_s3_client():
    """Return a boto3 S3 client configured for MinIO.

    Uses a module-level singleton -- the client is created on first call
    and reused for all subsequent calls. Thread-safe because boto3 clients
    are thread-safe for making API calls (but not for configuration changes).
    """
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
    return _s3_client
