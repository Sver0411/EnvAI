"""fix generation source uniqueness for multiple fields on one entity

Revision ID: f1c2d8e93a41
Revises: e8b1c7d92f30
"""
from alembic import op

revision = "f1c2d8e93a41"
down_revision = "e8b1c7d92f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_generation_source", "generation_sources", type_="unique")
    op.create_unique_constraint("uq_generation_source", "generation_sources", ["generation_run_id", "context_source_id"])


def downgrade() -> None:
    op.drop_constraint("uq_generation_source", "generation_sources", type_="unique")
    op.create_unique_constraint("uq_generation_source", "generation_sources", ["generation_run_id", "source_type", "source_id"])
