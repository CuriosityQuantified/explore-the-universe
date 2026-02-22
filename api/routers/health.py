import boto3
from botocore.client import Config
from fastapi import APIRouter, Response
from neo4j import GraphDatabase
from redis import Redis
from sqlalchemy import text

from api.db.session import engine
from shared.config import settings

router = APIRouter()


@router.get("/health")
def check_service_health(response: Response):
    services = {}
    all_services_healthy = True

    # PostgreSQL
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            postgres_version = result.scalar()
        services["postgresql"] = {
            "status": "connected",
            "version": postgres_version,
        }
    except Exception as exc:
        services["postgresql"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # Redis
    try:
        redis_client = Redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_client.close()
        services["redis"] = {"status": "connected"}
    except Exception as exc:
        services["redis"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # MinIO (S3-compatible)
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        bucket_list = [
            bucket["Name"]
            for bucket in s3_client.list_buckets()["Buckets"]
        ]
        services["minio"] = {
            "status": "connected",
            "buckets": bucket_list,
        }
    except Exception as exc:
        services["minio"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    # Neo4j
    try:
        neo4j_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        with neo4j_driver.session() as neo4j_session:
            result = neo4j_session.run(
                "CALL dbms.components() YIELD versions "
                "RETURN versions[0] AS version"
            )
            neo4j_version = result.single()["version"]
        neo4j_driver.close()
        services["neo4j"] = {
            "status": "connected",
            "version": neo4j_version,
        }
    except Exception as exc:
        services["neo4j"] = {
            "status": "disconnected",
            "error": str(exc),
        }
        all_services_healthy = False

    if not all_services_healthy:
        response.status_code = 503

    return {
        "status": "healthy" if all_services_healthy else "unhealthy",
        "services": services,
    }
