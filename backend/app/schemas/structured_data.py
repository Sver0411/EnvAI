from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VerificationStatus = Literal["ai_extracted", "user_verified"]
FactStatus = Literal["pending", "accepted", "rejected", "conflict", "superseded"]
ConflictStatus = Literal["open", "resolved", "ignored"]


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    annual_capacity: Decimal | None = None
    unit: str | None = None
    specification: str | None = None
    notes: str | None = None
    verification_status: VerificationStatus
    source_fact_id: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ProductionEquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    model: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    power: Decimal | None = None
    power_unit: str | None = None
    location: str | None = None
    notes: str | None = None
    verification_status: VerificationStatus
    source_fact_id: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class RawMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    annual_usage: Decimal | None = None
    annual_usage_unit: str | None = None
    max_storage: Decimal | None = None
    storage_unit: str | None = None
    storage_location: str | None = None
    cas_number: str | None = None
    physical_state: str | None = None
    hazardous: bool | None = None
    risk_material: bool | None = None
    notes: str | None = None
    verification_status: VerificationStatus
    source_fact_id: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class EnvironmentalFacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    facility_type: str
    quantity: Decimal | None = None
    unit: str | None = None
    treatment_target: str | None = None
    capacity: Decimal | None = None
    capacity_unit: str | None = None
    location: str | None = None
    notes: str | None = None
    verification_status: VerificationStatus
    source_fact_id: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ExtractedFactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    extraction_run_id: int
    project_file_id: int | None = None
    parsed_document_id: int | None = None
    entity_type: str
    entity_key: str
    field_name: str
    raw_value: str
    normalized_value: dict[str, Any] | None = None
    raw_unit: str | None = None
    unit: str | None = None
    confidence: Decimal | None = None
    source_type: str
    source_location: dict[str, Any] | None = None
    source_text: str | None = None
    status: FactStatus
    verification_status: str
    extractor_version: str
    prompt_version: str
    provider_name: str | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime
    source_filename: str | None = None


class ExtractionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: str
    schema_version: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    files_count: int
    facts_count: int
    conflicts_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_name: str | None = None
    model_name: str | None = None
    extractor_version: str
    prompt_version: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DataConflictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    extraction_run_id: int
    entity_type: str
    entity_key: str
    field_name: str
    value_a: str
    value_b: str
    fact_a_id: int | None = None
    fact_b_id: int | None = None
    source_a: dict[str, Any] | None = None
    source_b: dict[str, Any] | None = None
    status: ConflictStatus
    resolution: str | None = None
    resolved_by: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StructuredProjectDataOut(BaseModel):
    profile: dict[str, Any] | None = None
    products: list[ProductOut] = Field(default_factory=list)
    equipment: list[ProductionEquipmentOut] = Field(default_factory=list)
    raw_materials: list[RawMaterialOut] = Field(default_factory=list)
    environmental_facilities: list[EnvironmentalFacilityOut] = Field(default_factory=list)
    facts: list[ExtractedFactOut] = Field(default_factory=list)
    conflicts: list[DataConflictOut] = Field(default_factory=list)
    latest_run: ExtractionRunOut | None = None


class StructuredDataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    annual_capacity: Decimal | None = None
    unit: str | None = None
    annual_usage: Decimal | None = None
    annual_usage_unit: str | None = None
    max_storage: Decimal | None = None
    storage_unit: str | None = None
    storage_location: str | None = None
    model: str | None = None
    quantity: Decimal | None = None
    notes: str | None = None


class ConflictResolveIn(BaseModel):
    resolution: Literal["use_a", "use_b", "ignore"]
    note: str | None = Field(default=None, max_length=500)
