"""add classification tables and catalog columns

Revision ID: a1b2c3d4e5f6
Revises: 2abf67c31898
Create Date: 2026-08-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2abf67c31898"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add object_classifications table and 3 catalog columns to astronomical_objects."""
    # --- New table: object_classifications (append-only ML classification history) ---
    op.create_table(
        "object_classifications",
        sa.Column("classification_uuid", sa.UUID(), nullable=False),
        sa.Column("object_uuid", sa.UUID(), nullable=False),
        sa.Column("predicted_object_type", sa.String(), nullable=False),
        sa.Column("classification_confidence_score", sa.Float(), nullable=False),
        sa.Column("ml_model_version", sa.String(), nullable=False),
        sa.Column("feature_extractor_version", sa.String(), nullable=False),
        sa.Column(
            "feature_vector",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_anomaly_flagged", sa.Boolean(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("anomaly_explanation", sa.Text(), nullable=True),
        sa.Column(
            "classified_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["object_uuid"],
            ["astronomical_objects.object_uuid"],
        ),
        sa.PrimaryKeyConstraint("classification_uuid"),
    )

    # --- New columns on astronomical_objects ---
    op.add_column(
        "astronomical_objects",
        sa.Column("catalog_object_name", sa.String(), nullable=True),
    )
    op.add_column(
        "astronomical_objects",
        sa.Column("catalog_magnitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "astronomical_objects",
        sa.Column("catalog_redshift", sa.Float(), nullable=True),
    )

    # Index for catalog_object_name (used in cross-match lookups)
    op.create_index(
        "ix_astronomical_objects_catalog_object_name",
        "astronomical_objects",
        ["catalog_object_name"],
    )


def downgrade() -> None:
    """Remove object_classifications table and 3 catalog columns."""
    op.drop_index(
        "ix_astronomical_objects_catalog_object_name",
        table_name="astronomical_objects",
    )
    op.drop_column("astronomical_objects", "catalog_redshift")
    op.drop_column("astronomical_objects", "catalog_magnitude")
    op.drop_column("astronomical_objects", "catalog_object_name")
    op.drop_table("object_classifications")
