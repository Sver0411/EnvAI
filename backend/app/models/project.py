from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner = relationship("User", back_populates="projects")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    company_profiles = relationship("CompanyProfile", back_populates="project", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="project", cascade="all, delete-orphan")
    equipment = relationship("ProductionEquipment", back_populates="project", cascade="all, delete-orphan")
    raw_materials = relationship("RawMaterial", back_populates="project", cascade="all, delete-orphan")
    environmental_facilities = relationship(
        "EnvironmentalFacility", back_populates="project", cascade="all, delete-orphan"
    )
    extraction_runs = relationship("ExtractionRun", back_populates="project", cascade="all, delete-orphan")
    extracted_facts = relationship("ExtractedFact", back_populates="project", cascade="all, delete-orphan")
    data_conflicts = relationship("DataConflict", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "project_type IN ('environmental_impact', 'emergency_response', 'risk_assessment', 'other')",
            name="ck_projects_project_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'collecting_data', 'analyzing', 'generating', 'reviewing', 'completed')",
            name="ck_projects_status",
        ),
    )
