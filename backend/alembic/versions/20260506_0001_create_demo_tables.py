"""create demo tables.

Revision ID: 20260506_0001
Revises: None
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260506_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    demo_status = postgresql.ENUM(
        "ACTIVE",
        "EXPIRED",
        "DISABLED",
        name="demostatus",
        create_type=False,
    )
    demo_file_status = postgresql.ENUM(
        "COMPLETED",
        "FAILED",
        name="demofilestatus",
        create_type=False,
    )
    demo_file_type = postgresql.ENUM(
        "URL",
        "PDF",
        name="demofiletype",
        create_type=False,
    )
    demo_status.create(op.get_bind(), checkfirst=True)
    demo_file_status.create(op.get_bind(), checkfirst=True)
    demo_file_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "instarag_agent_demos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prospect_name", sa.String(length=255), nullable=False),
        sa.Column("company_url", sa.String(length=1024), nullable=False),
        sa.Column("logo_url", sa.String(length=1024), nullable=True),
        sa.Column("vector_store_id", sa.String(length=255), nullable=False),
        sa.Column("public_slug", sa.String(length=255), nullable=False),
        sa.Column("access_password", sa.String(length=255), nullable=True),
        sa.Column("status", demo_status, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("public_slug"),
        sa.UniqueConstraint("vector_store_id"),
    )

    op.create_table(
        "instarag_agent_demo_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("demo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", sa.String(length=255), nullable=False),
        sa.Column("vector_store_file_id", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", demo_file_type, nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", demo_file_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["demo_id"], ["instarag_agent_demos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("vector_store_file_id"),
    )
    op.create_index(
        "ix_instarag_agent_demos_status_expires_at",
        "instarag_agent_demos",
        ["status", "expires_at"],
    )
    op.create_index(
        "ix_instarag_agent_demos_created_at",
        "instarag_agent_demos",
        ["created_at"],
    )
    op.create_index(
        "ix_instarag_agent_demo_files_demo_id",
        "instarag_agent_demo_files",
        ["demo_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_instarag_agent_demo_files_demo_id", table_name="instarag_agent_demo_files")
    op.drop_index("ix_instarag_agent_demos_created_at", table_name="instarag_agent_demos")
    op.drop_index("ix_instarag_agent_demos_status_expires_at", table_name="instarag_agent_demos")
    op.drop_table("instarag_agent_demo_files")
    op.drop_table("instarag_agent_demos")
    postgresql.ENUM(name="demofiletype").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="demofilestatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="demostatus").drop(op.get_bind(), checkfirst=True)
