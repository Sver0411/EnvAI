from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    uploader_id: int
    filename: str
    file_type: str | None
    file_size: int
    storage_path: str | None
    parse_status: str
    created_at: datetime
    updated_at: datetime
