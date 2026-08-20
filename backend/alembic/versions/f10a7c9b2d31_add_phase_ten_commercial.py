"""add phase ten platform operations and commercial foundation"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f10a7c9b2d31"
down_revision = "d9a3b7c51f20"
branch_labels = None
depends_on = None
jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("users", sa.Column("platform_role", sa.String(32), server_default="user", nullable=False))
    op.add_column("users", sa.Column("status", sa.String(32), server_default="active", nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_platform_role", "users", ["platform_role"])
    op.create_index("ix_users_status", "users", ["status"])
    op.add_column("organizations", sa.Column("suspension_reason", sa.Text(), nullable=True))
    op.add_column("organizations", sa.Column("suspended_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("organizations", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    for name, col in [
        ("description", sa.Column("description", sa.Text(), nullable=True)),
        ("status", sa.Column("status", sa.String(32), server_default="active", nullable=False)),
        ("billing_period", sa.Column("billing_period", sa.String(16), server_default="month", nullable=False)),
        ("price_amount", sa.Column("price_amount", sa.Numeric(12, 2), server_default="0", nullable=False)),
        ("price_currency", sa.Column("price_currency", sa.String(3), server_default="CNY", nullable=False)),
        ("display_order", sa.Column("display_order", sa.Integer(), server_default="0", nullable=False)),
        ("is_public", sa.Column("is_public", sa.Boolean(), server_default=sa.true(), nullable=False)),
        ("trial_days", sa.Column("trial_days", sa.Integer(), server_default="0", nullable=False)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)),
    ]: op.add_column("plans", col)
    op.create_index("ix_plans_status", "plans", ["status"])
    op.create_table("organization_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("current_period_start", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("price_amount", sa.Numeric(12, 2), server_default="0", nullable=False), sa.Column("price_currency", sa.String(3), server_default="CNY", nullable=False),
        sa.Column("billing_provider", sa.String(32), server_default="manual", nullable=False), sa.Column("external_subscription_id", sa.String(255), unique=True),
        sa.Column("entitlement_snapshot", jsonb), sa.Column("next_plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="SET NULL")), sa.Column("change_effective_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("organization_id", name="uq_org_subscription_org"))
    op.create_index("ix_organization_subscriptions_organization_id", "organization_subscriptions", ["organization_id"])
    op.create_index("ix_organization_subscriptions_status", "organization_subscriptions", ["status"])
    op.create_table("billing_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("billing_name", sa.String(255)), sa.Column("tax_id", sa.String(128)), sa.Column("contact_name", sa.String(128)), sa.Column("contact_email", sa.String(255)), sa.Column("billing_address", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("organization_id", name="uq_billing_account_org"))
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("order_number", sa.String(64), nullable=False), sa.Column("order_type", sa.String(32), server_default="subscription", nullable=False), sa.Column("status", sa.String(32), server_default="pending", nullable=False), sa.Column("currency", sa.String(3), server_default="CNY", nullable=False), sa.Column("subtotal", sa.Numeric(12, 2), nullable=False), sa.Column("discount_amount", sa.Numeric(12, 2), server_default="0", nullable=False), sa.Column("total_amount", sa.Numeric(12, 2), nullable=False), sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT")), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("order_number", name="uq_orders_number"))
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"]); op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table("payment_attempts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("status", sa.String(32), server_default="pending", nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("external_payment_id", sa.String(255)), sa.Column("request_id", sa.String(128), nullable=False), sa.Column("idempotency_key", sa.String(128), unique=True), sa.Column("error_code", sa.String(64)), sa.Column("error_message", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("provider", "external_payment_id", name="uq_payment_external"), sa.UniqueConstraint("provider", "request_id", name="uq_payment_request"))
    op.create_index("ix_payment_attempts_order_id", "payment_attempts", ["order_id"])
    op.create_table("ai_model_pricing", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("provider", sa.String(64), nullable=False), sa.Column("model", sa.String(128), nullable=False), sa.Column("usage_type", sa.String(32), server_default="llm", nullable=False), sa.Column("currency", sa.String(3), server_default="CNY", nullable=False), sa.Column("input_price_per_million_tokens", sa.Numeric(18, 8), server_default="0", nullable=False), sa.Column("output_price_per_million_tokens", sa.Numeric(18, 8), server_default="0", nullable=False), sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False), sa.Column("effective_to", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("provider", "model", "effective_from", name="uq_ai_pricing_version"))
    op.create_index("ix_ai_model_pricing_provider", "ai_model_pricing", ["provider"]); op.create_index("ix_ai_model_pricing_model", "ai_model_pricing", ["model"])
    op.create_table("usage_costs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("usage_event_id", sa.Integer(), sa.ForeignKey("usage_events.id", ondelete="CASCADE"), nullable=False), sa.Column("pricing_id", sa.Integer(), sa.ForeignKey("ai_model_pricing.id", ondelete="SET NULL")), sa.Column("estimated_cost", sa.Numeric(18, 8), server_default="0", nullable=False), sa.Column("cost_currency", sa.String(3), server_default="CNY", nullable=False), sa.Column("is_estimated", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("usage_event_id", name="uq_usage_cost_event"))
    op.create_table("feature_flags", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(128), nullable=False), sa.Column("description", sa.Text()), sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("key", "organization_id", name="uq_feature_flag_scope"))
    op.create_index("ix_feature_flags_key", "feature_flags", ["key"]); op.create_index("ix_feature_flags_organization_id", "feature_flags", ["organization_id"])
    op.create_table("system_announcements", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("type", sa.String(32), server_default="info", nullable=False), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("audience", sa.String(32), server_default="all", nullable=False), sa.Column("organization_ids", jsonb), sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_table("quota_adjustments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("quota_type", sa.String(64), nullable=False), sa.Column("amount", sa.BigInteger(), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("period_start", sa.DateTime(timezone=True), nullable=False), sa.Column("period_end", sa.DateTime(timezone=True), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_quota_adjustments_organization_id", "quota_adjustments", ["organization_id"])
    op.create_table("platform_audit_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="SET NULL")), sa.Column("action", sa.String(128), nullable=False), sa.Column("target_type", sa.String(64)), sa.Column("target_id", sa.String(128)), sa.Column("metadata", jsonb), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_platform_audit_events_actor_user_id", "platform_audit_events", ["actor_user_id"])
    op.execute("UPDATE plans SET status = CASE WHEN active THEN 'active' ELSE 'inactive' END")
    op.execute("INSERT INTO organization_subscriptions (organization_id, plan_id, price_amount, price_currency, entitlement_snapshot) SELECT o.id, p.id, p.price_amount, p.price_currency, jsonb_build_object('max_members', p.member_limit, 'max_projects', p.project_limit, 'monthly_llm_tokens', p.ai_token_limit, 'storage_bytes', p.storage_bytes_limit, 'features', COALESCE(p.features, '{}'::jsonb), 'plan_id', p.id) FROM organizations o JOIN plans p ON p.id=o.plan_id ON CONFLICT (organization_id) DO NOTHING")


def downgrade() -> None:
    for table in ("platform_audit_events", "quota_adjustments", "system_announcements", "feature_flags", "usage_costs", "ai_model_pricing", "payment_attempts", "orders", "billing_accounts", "organization_subscriptions"): op.drop_table(table)
    for name in ("suspension_reason", "suspended_by", "suspended_at"): op.drop_column("organizations", name)
    for name in ("description", "status", "billing_period", "price_amount", "price_currency", "display_order", "is_public", "trial_days", "updated_at"): op.drop_column("plans", name)
    op.drop_index("ix_users_platform_role", table_name="users"); op.drop_index("ix_users_status", table_name="users")
    for name in ("platform_role", "status", "last_login_at"): op.drop_column("users", name)
