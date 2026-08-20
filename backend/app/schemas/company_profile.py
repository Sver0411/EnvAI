from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CompanyProfileWrite(BaseModel):
    company_name: str | None = None
    credit_code: str | None = None
    legal_representative: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    registered_address: str | None = None
    project_address: str | None = None
    industry_category: str | None = None
    industry_code: str | None = None
    business_scope: str | None = None
    land_area: str | None = None
    building_area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # 生产信息
    products: str | None = None
    annual_output: str | None = None
    production_process: str | None = None
    equipment: list[dict] | None = None
    # 原辅材料：{name, annual_usage, unit, max_storage, storage_location, cas_number}
    raw_materials: list[dict] | None = None
    pollution_control: dict[str, Any] | None = None
    risk_substances: dict[str, Any] | None = None


class CompanyProfileOut(CompanyProfileWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
