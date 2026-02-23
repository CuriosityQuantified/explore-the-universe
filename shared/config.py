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

    # Segmentation
    s3_bucket_segmentation: str = "segmentation"
    sam3_model_checkpoint_path: str = ""  # Local path to SAM 3 checkpoint (empty = auto-download from HuggingFace)
    sam3_bpe_path: str = ""  # Path to bpe_simple_vocab_16e6.txt.gz for SAM 3 text prompts
    segmentation_detection_threshold_sigma: float = 1.5
    segmentation_min_area_pixels: int = 5
    segmentation_deblend_nthresh: int = 32
    segmentation_deblend_contrast: float = 0.005
    segmentation_background_box_size: int = 64
    segmentation_sub_region_size: int = 1024
    segmentation_sub_sub_region_size: int = 256
    segmentation_overlap_fraction: float = 0.2
    segmentation_snr_high_threshold: float = 10.0
    segmentation_snr_medium_threshold: float = 3.0
    segmentation_cutout_padding_fraction: float = 0.1
    segmentation_boundary_iou_threshold: float = 0.5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
