"""add parsed document results

Revision ID: 9c27e8a1f4b2
Revises: 6f4b8a39d21c
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9c27e8a1f4b2"
down_revision = "6f4b8a39d21c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parsed_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_file_id", sa.Integer(), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=True),
        sa.Column("structured_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_file_id"], ["project_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_file_id"),
    )
    op.create_index(op.f("ix_parsed_documents_id"), "parsed_documents", ["id"], unique=False)
    op.create_index(op.f("ix_parsed_documents_project_file_id"), "parsed_documents", ["project_file_id"], unique=True)
    op.create_check_constraint(
        "ck_parsed_documents_status",
        "parsed_documents",
        "status IN ('pending', 'parsing', 'parsed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_parsed_documents_status", "parsed_documents", type_="check")
    op.drop_index(op.f("ix_parsed_documents_project_file_id"), table_name="parsed_documents")
    op.drop_index(op.f("ix_parsed_documents_id"), table_name="parsed_documents")
    op.drop_table("parsed_documents")
