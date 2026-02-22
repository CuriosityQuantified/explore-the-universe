from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql://explorer:explorer_dev@localhost:5432/explore_universe"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_result_backend_url: str = "redis://localhost:6379/1"

    # MinIO (S3-compatible object storage)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_fits_raw: str = "fits-raw"
    s3_bucket_tiles: str = "tiles"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_dev_password"

    # MAST (Mikulski Archive for Space Telescopes)
    mast_api_token: str = ""  # Empty string = public data only, no auth needed for public JWST data
    mast_download_directory: str = "/tmp/mast_downloads"  # Local temp dir for downloads before MinIO upload

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
