"""add phase nine tenant, membership and usage foundations

Revision ID: d9a3b7c51f20
Revises: c8f2a7d91e64
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d9a3b7c51f20"
down_revision = "c8f2a7d91e64"
branch_labels = None
depends_on = None
jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table("plans", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), sa.Column("member_limit", sa.Integer(), server_default="5", nullable=False), sa.Column("project_limit", sa.Integer(), server_default="20", nullable=False), sa.Column("ai_token_limit", sa.BigInteger(), server_default="1000000", nullable=False), sa.Column("storage_bytes_limit", sa.BigInteger(), server_default="5368709120", nullable=False), sa.Column("features", jsonb), sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False), sa.UniqueConstraint("code", name="uq_plans_code"))
    op.create_index("ix_plans_id", "plans", ["id"])
    op.create_table("organizations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("slug", sa.String(128), nullable=False), sa.Column("status", sa.String(32), server_default="active", nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("slug", name="uq_organizations_slug"), sa.CheckConstraint("status IN ('active', 'suspended', 'archived')", name="ck_organizations_status"))
    op.create_index("ix_organizations_id", "organizations", ["id"])
    op.create_table("organization_members", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(32), server_default="member", nullable=False), sa.Column("status", sa.String(32), server_default="active", nullable=False), sa.Column("joined_at", sa.DateTime(timezone=True)), sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_member"), sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="ck_organization_members_role"), sa.CheckConstraint("status IN ('invited', 'active', 'suspended', 'removed')", name="ck_organization_members_status"))
    op.create_index("ix_organization_members_id", "organization_members", ["id"]); op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"]); op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_table("project_members", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("project_role", sa.String(32), server_default="viewer", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"), sa.CheckConstraint("project_role IN ('owner', 'editor', 'reviewer', 'viewer')", name="ck_project_members_role"))
    op.create_index("ix_project_members_id", "project_members", ["id"]); op.create_index("ix_project_members_project_id", "project_members", ["project_id"]); op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_table("organization_invitations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(255), nullable=False), sa.Column("role", sa.String(32), server_default="member", nullable=False), sa.Column("token_hash", sa.String(128), nullable=False), sa.Column("status", sa.String(32), server_default="pending", nullable=False), sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("token_hash", name="uq_organization_invitation_token"), sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name="ck_organization_invitations_role"), sa.CheckConstraint("status IN ('pending', 'accepted', 'expired', 'revoked')", name="ck_organization_invitations_status"))
    op.create_index("ix_organization_invitations_id", "organization_invitations", ["id"]); op.create_index("ix_organization_invitations_organization_id", "organization_invitations", ["organization_id"]); op.create_index("ix_organization_invitations_email", "organization_invitations", ["email"])
    op.create_table("usage_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL")), sa.Column("usage_type", sa.String(64), nullable=False), sa.Column("quantity", sa.BigInteger(), nullable=False), sa.Column("unit", sa.String(32), nullable=False), sa.Column("provider", sa.String(64)), sa.Column("model", sa.String(128)), sa.Column("related_resource_type", sa.String(64)), sa.Column("related_resource_id", sa.Integer()), sa.Column("source_key", sa.String(255), nullable=False), sa.Column("metadata", jsonb), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("organization_id", "source_key", name="uq_usage_event_source"), sa.CheckConstraint("usage_type IN ('llm_input_tokens', 'llm_output_tokens', 'embedding_tokens', 'document_parse', 'ocr_page', 'storage_bytes', 'docx_export', 'pdf_export')", name="ck_usage_events_type"))
    op.create_index("ix_usage_events_id", "usage_events", ["id"]); op.create_index("ix_usage_events_organization_id", "usage_events", ["organization_id"])
    for table in ("projects", "knowledge_bases", "document_instances", "report_templates", "report_snapshots"):
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.create_foreign_key("fk_projects_organization_id", "projects", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_knowledge_bases_organization_id", "knowledge_bases", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_document_instances_organization_id", "document_instances", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_report_templates_organization_id", "report_templates", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_report_snapshots_organization_id", "report_snapshots", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.execute("INSERT INTO plans (code, name) VALUES ('local_mvp', 'EnvAI 本地 MVP') ON CONFLICT (code) DO NOTHING")
    op.execute("INSERT INTO organizations (name, slug, created_by, plan_id) SELECT COALESCE(full_name, username) || ' 的工作区', 'personal-' || id, id, (SELECT id FROM plans WHERE code='local_mvp') FROM users ON CONFLICT (slug) DO NOTHING")
    op.execute("INSERT INTO organization_members (organization_id, user_id, role, status, joined_at) SELECT id, created_by, 'owner', 'active', now() FROM organizations ON CONFLICT (organization_id, user_id) DO NOTHING")
    op.execute("UPDATE projects p SET organization_id = o.id FROM organizations o WHERE p.organization_id IS NULL AND o.created_by = p.owner_id")
    op.execute("INSERT INTO project_members (project_id, user_id, project_role) SELECT id, owner_id, 'owner' FROM projects ON CONFLICT (project_id, user_id) DO NOTHING")
    op.execute("UPDATE knowledge_bases k SET organization_id = o.id FROM organizations o WHERE k.organization_id IS NULL AND o.created_by = k.created_by")
    op.execute("UPDATE document_instances d SET organization_id = p.organization_id FROM projects p WHERE d.organization_id IS NULL AND d.project_id = p.id")
    op.execute("UPDATE report_templates r SET organization_id = o.id FROM organizations o WHERE r.organization_id IS NULL AND r.created_by = o.created_by")
    op.execute("UPDATE report_snapshots s SET organization_id = d.organization_id FROM document_instances d WHERE s.organization_id IS NULL AND s.document_instance_id = d.id")


def downgrade() -> None:
    for table in ("report_snapshots", "report_templates", "document_instances", "knowledge_bases", "projects"):
        op.drop_constraint(f"fk_{table}_organization_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_organization_id", table_name=table); op.drop_column(table, "organization_id")
    for table in ("usage_events", "organization_invitations", "project_members", "organization_members", "organizations", "plans"):
        op.drop_table(table)
