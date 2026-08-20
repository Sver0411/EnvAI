"""add phase three structured extraction data

Revision ID: b7e4c2d91a30
Revises: 9c27e8a1f4b2
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b7e4c2d91a30"
down_revision = "9c27e8a1f4b2"
branch_labels = None
depends_on = None
jsonb = postgresql.JSONB(astext_type=sa.Text())


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("company_profiles", sa.Column("registered_address", sa.String(length=255), nullable=True))
    op.add_column("company_profiles", sa.Column("industry_code", sa.String(length=64), nullable=True))
    op.add_column("company_profiles", sa.Column("business_scope", sa.Text(), nullable=True))
    op.add_column("company_profiles", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("company_profiles", sa.Column("longitude", sa.Numeric(10, 7), nullable=True))

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("schema_version", sa.String(length=32), server_default="v1", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("files_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("facts_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conflicts_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("extractor_version", sa.String(length=32), server_default="rule-v1", nullable=False),
        sa.Column("prompt_version", sa.String(length=64), server_default="structured-v1", nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'partial')",
            name="ck_extraction_runs_status",
        ),
    )
    op.create_index("ix_extraction_runs_id", "extraction_runs", ["id"])
    op.create_index("ix_extraction_runs_project_id", "extraction_runs", ["project_id"])

    op.create_table(
        "extracted_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("extraction_run_id", sa.Integer(), nullable=False),
        sa.Column("project_file_id", sa.Integer(), nullable=True),
        sa.Column("parsed_document_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=False),
        sa.Column("normalized_value", jsonb, nullable=True),
        sa.Column("raw_unit", sa.String(length=32), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("source_type", sa.String(length=32), server_default="rule", nullable=False),
        sa.Column("source_location", jsonb, nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("verification_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("extractor_version", sa.String(length=32), server_default="rule-v1", nullable=False),
        sa.Column("prompt_version", sa.String(length=64), server_default="structured-v1", nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_file_id"], ["project_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parsed_document_id"], ["parsed_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'conflict', 'superseded')",
            name="ck_extracted_facts_status",
        ),
    )
    op.create_index("ix_extracted_facts_id", "extracted_facts", ["id"])
    op.create_index("ix_extracted_facts_project_id", "extracted_facts", ["project_id"])
    op.create_index("ix_extracted_facts_extraction_run_id", "extracted_facts", ["extraction_run_id"])
    op.create_index("ix_extracted_facts_project_file_id", "extracted_facts", ["project_file_id"])

    def common_columns():
        return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("verification_status", sa.String(length=32), server_default="ai_extracted", nullable=False),
        sa.Column("source_fact_id", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        *_timestamps(),
        ]

    op.create_table(
        "products",
        *common_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("annual_capacity", sa.Numeric(20, 6), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("specification", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_fact_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("verification_status IN ('ai_extracted', 'user_verified')", name="ck_products_verification_status"),
    )
    op.create_table(
        "production_equipment",
        *common_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("power", sa.Numeric(20, 6), nullable=True),
        sa.Column("power_unit", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_fact_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("verification_status IN ('ai_extracted', 'user_verified')", name="ck_production_equipment_verification_status"),
    )
    op.create_table(
        "raw_materials",
        *common_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("annual_usage", sa.Numeric(20, 6), nullable=True),
        sa.Column("annual_usage_unit", sa.String(length=32), nullable=True),
        sa.Column("max_storage", sa.Numeric(20, 6), nullable=True),
        sa.Column("storage_unit", sa.String(length=32), nullable=True),
        sa.Column("storage_location", sa.String(length=255), nullable=True),
        sa.Column("cas_number", sa.String(length=64), nullable=True),
        sa.Column("physical_state", sa.String(length=32), nullable=True),
        sa.Column("hazardous", sa.Boolean(), nullable=True),
        sa.Column("risk_material", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_fact_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("verification_status IN ('ai_extracted', 'user_verified')", name="ck_raw_materials_verification_status"),
    )
    op.create_table(
        "environmental_facilities",
        *common_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("facility_type", sa.String(length=32), server_default="other", nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("treatment_target", sa.String(length=255), nullable=True),
        sa.Column("capacity", sa.Numeric(20, 6), nullable=True),
        sa.Column("capacity_unit", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_fact_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("verification_status IN ('ai_extracted', 'user_verified')", name="ck_environmental_facilities_verification_status"),
    )
    for table in ("products", "production_equipment", "raw_materials", "environmental_facilities"):
        op.create_index(f"ix_{table}_id", table, ["id"])
        op.create_index(f"ix_{table}_project_id", table, ["project_id"])

    op.create_table(
        "data_conflicts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("extraction_run_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("value_a", sa.Text(), nullable=False),
        sa.Column("value_b", sa.Text(), nullable=False),
        sa.Column("fact_a_id", sa.Integer(), nullable=True),
        sa.Column("fact_b_id", sa.Integer(), nullable=True),
        sa.Column("source_a", jsonb, nullable=True),
        sa.Column("source_b", jsonb, nullable=True),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fact_a_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fact_b_id"], ["extracted_facts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('open', 'resolved', 'ignored')", name="ck_data_conflicts_status"),
    )
    op.create_index("ix_data_conflicts_id", "data_conflicts", ["id"])
    op.create_index("ix_data_conflicts_project_id", "data_conflicts", ["project_id"])
    op.create_index("ix_data_conflicts_extraction_run_id", "data_conflicts", ["extraction_run_id"])


def downgrade() -> None:
    for index, table in (
        ("ix_data_conflicts_extraction_run_id", "data_conflicts"),
        ("ix_data_conflicts_project_id", "data_conflicts"),
        ("ix_data_conflicts_id", "data_conflicts"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("data_conflicts")
    for table in ("environmental_facilities", "raw_materials", "production_equipment", "products"):
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_index(f"ix_{table}_id", table_name=table)
        op.drop_table(table)
    for index, table in (
        ("ix_extracted_facts_project_file_id", "extracted_facts"),
        ("ix_extracted_facts_extraction_run_id", "extracted_facts"),
        ("ix_extracted_facts_project_id", "extracted_facts"),
        ("ix_extracted_facts_id", "extracted_facts"),
        ("ix_extraction_runs_project_id", "extraction_runs"),
        ("ix_extraction_runs_id", "extraction_runs"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("extracted_facts")
    op.drop_table("extraction_runs")
    for column in ("longitude", "latitude", "business_scope", "industry_code", "registered_address"):
        op.drop_column("company_profiles", column)
