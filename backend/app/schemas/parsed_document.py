from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ParseStatus = Literal["pending", "parsing", "parsed", "failed"]


class ParsedDocumentStatusOut(BaseModel):
    project_file_id: int
    status: ParseStatus
    parser_name: str | None = None
    parser_version: str | None = None
    error_message: str | None = None
    parsed_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)


class ParsedDocumentOut(ParsedDocumentStatusOut):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plain_text: str | None = None
    structured_content: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="document_metadata")
    created_at: datetime
    updated_at: datetime
