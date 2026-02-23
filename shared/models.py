import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class PipelineStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class StepStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class DetectionConfidenceTier(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Observation(Base):
    __tablename__ = "observations"

    observation_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    archive_observation_id = Column(String, unique=True, nullable=False)
    archive_program_id = Column(String, nullable=True)
    telescope_name = Column(String, nullable=False)
    instrument_name = Column(String, nullable=False)
    spectral_filters = Column(JSONB, nullable=True)
    total_exposure_seconds = Column(Float, nullable=True)
    pointing_ra_degrees = Column(Float, nullable=True)
    pointing_dec_degrees = Column(Float, nullable=True)
    pipeline_status = Column(
        Enum(PipelineStatus, name="pipeline_status_enum"),
        nullable=False,
        default=PipelineStatus.pending,
    )
    ingested_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    last_updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    processing_steps = relationship(
        "ProcessingStep", back_populates="observation"
    )
    astronomical_objects = relationship(
        "AstronomicalObject", back_populates="source_observation"
    )


class ProcessingStep(Base):
    __tablename__ = "processing_steps"

    step_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    observation_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("observations.observation_uuid"),
        nullable=False,
    )
    step_name = Column(String, nullable=False)
    step_status = Column(
        Enum(StepStatus, name="step_status_enum"),
        nullable=False,
        default=StepStatus.pending,
    )
    step_started_at = Column(TIMESTAMP, nullable=True)
    step_completed_at = Column(TIMESTAMP, nullable=True)
    error_message_text = Column(Text, nullable=True)
    step_output_metadata = Column(JSONB, nullable=True)

    # Relationships
    observation = relationship(
        "Observation", back_populates="processing_steps"
    )


class AstronomicalObject(Base):
    __tablename__ = "astronomical_objects"

    object_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_observation_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("observations.observation_uuid"),
        nullable=False,
    )
    sky_coordinate_ra_degrees = Column(Float, nullable=False)
    sky_coordinate_dec_degrees = Column(Float, nullable=False)
    classified_object_type = Column(String, nullable=True)
    classification_source_catalog = Column(String, nullable=True)
    classification_confidence_score = Column(Float, nullable=True)
    physical_properties = Column(JSONB, nullable=True)
    is_anomaly_flagged = Column(Boolean, default=False, nullable=False)
    segmentation_mask_rle = Column(JSONB, nullable=True)
    cutout_s3_prefix = Column(String, nullable=True)
    bounding_box_pixels = Column(JSONB, nullable=True)
    detection_signal_to_noise_ratio = Column(Float, nullable=True)
    detection_confidence_tier = Column(
        Enum(DetectionConfidenceTier, name="detection_confidence_tier_enum"),
        nullable=True,
    )
    detection_scale_level = Column(String, nullable=True)
    is_edge_detection = Column(Boolean, default=False, nullable=False)
    pixel_centroid_x = Column(Float, nullable=True)
    pixel_centroid_y = Column(Float, nullable=True)
    segmentation_method = Column(String, nullable=True)
    detected_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    source_observation = relationship(
        "Observation", back_populates="astronomical_objects"
    )
    catalog_cross_matches = relationship(
        "CatalogCrossMatch", back_populates="astronomical_object"
    )


class CatalogCrossMatch(Base):
    __tablename__ = "catalog_cross_matches"

    match_uuid = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    object_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("astronomical_objects.object_uuid"),
        nullable=False,
    )
    catalog_name = Column(String, nullable=False)
    catalog_source_id = Column(String, nullable=False)
    angular_separation_arcseconds = Column(Float, nullable=False)
    match_probability_score = Column(Float, nullable=True)
    raw_catalog_response = Column(JSONB, nullable=True)

    # Relationships
    astronomical_object = relationship(
        "AstronomicalObject", back_populates="catalog_cross_matches"
    )
