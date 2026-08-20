"""add operation classification to usage events"""
from alembic import op
import sqlalchemy as sa

revision = "f10b8c7d3e42"
down_revision = "f10a7c9b2d31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usage_events", sa.Column("operation", sa.String(64), nullable=True))
    op.create_index("ix_usage_events_operation", "usage_events", ["operation"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_operation", table_name="usage_events")
    op.drop_column("usage_events", "operation")

