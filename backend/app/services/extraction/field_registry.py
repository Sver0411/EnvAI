"""Phase 3 当前支持字段的单一规范入口。"""

FIELD_REGISTRY = {
    "company_profile": {
        "company_name": "string",
        "project_address": "string",
        "legal_representative": "string",
        "industry_category": "string",
    },
    "product": {"name": "string", "annual_capacity": "decimal", "unit": "unit"},
    "production_equipment": {"name": "string", "model": "string", "quantity": "decimal", "unit": "unit"},
    "raw_material": {
        "name": "string",
        "annual_usage": "decimal",
        "annual_usage_unit": "unit",
        "max_storage": "decimal",
        "storage_unit": "unit",
        "storage_location": "string",
        "cas_number": "string",
    },
    "environmental_facility": {"name": "string", "facility_type": "string"},
}
