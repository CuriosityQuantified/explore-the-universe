import uuid

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from shared.config import settings
from shared.models import Observation, PipelineStatus

router = APIRouter()


@router.post("/test/upload")
def upload_test_file(
    file: UploadFile = File(...),
    database_session: Session = Depends(get_database_session),
):
    """Temporary test endpoint: uploads a file to MinIO and creates
    an observation metadata record in PostgreSQL.

    This endpoint validates success criterion #4 and will be removed
    or moved behind an admin flag in later phases.
    """
    new_observation_uuid = uuid.uuid4()
    object_key = f"raw/{new_observation_uuid}/{file.filename}"

    # Upload file to MinIO
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )
    s3_client.upload_fileobj(
        file.file, settings.s3_bucket_fits_raw, object_key
    )

    # Create metadata record in PostgreSQL
    observation_record = Observation(
        observation_uuid=new_observation_uuid,
        archive_observation_id=f"test-{new_observation_uuid}",
        telescope_name="test",
        instrument_name="test",
        pipeline_status=PipelineStatus.pending,
    )
    database_session.add(observation_record)
    database_session.commit()

    return {
        "observation_uuid": str(new_observation_uuid),
        "object_key": object_key,
        "bucket": settings.s3_bucket_fits_raw,
    }
