"""add phase one data constraints

Revision ID: 6f4b8a39d21c
Revises: 8528d086ee2b
Create Date: 2026-08-19
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "6f4b8a39d21c"
down_revision = "8528d086ee2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_company_profiles_project_id",
        "company_profiles",
        ["project_id"],
    )
    op.create_check_constraint(
        "ck_projects_project_type",
        "projects",
        "project_type IN ('environmental_impact', 'emergency_response', 'risk_assessment', 'other')",
    )
    op.create_check_constraint(
        "ck_projects_status",
        "projects",
        "status IN ('draft', 'collecting_data', 'analyzing', 'generating', 'reviewing', 'completed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_projects_status", "projects", type_="check")
    op.drop_constraint("ck_projects_project_type", "projects", type_="check")
    op.drop_constraint("uq_company_profiles_project_id", "company_profiles", type_="unique")
