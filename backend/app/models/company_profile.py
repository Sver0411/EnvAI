from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (UniqueConstraint("project_id", name="uq_company_profiles_project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # 企业基本信息
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credit_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_representative: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    registered_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    building_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    # 生产信息
    products: Mapped[str | None] = mapped_column(Text, nullable=True)
    annual_output: Mapped[str | None] = mapped_column(String(128), nullable=True)
    production_process: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment: Mapped[str | None] = mapped_column(JSON, nullable=True)
    # 原辅材料（Phase 1 以 JSONB 存储，Phase 3 结构化时拆分为独立表）
    raw_materials: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 污染治理 / 环境风险信息（JSONB，按污染物类型组织）
    pollution_control: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_substances: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="company_profiles")
