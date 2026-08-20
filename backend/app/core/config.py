import json
import tempfile
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated as _Annotated
from sqlalchemy.engine import make_url

# 让 pydantic-settings 不对该字段做预解码，交由下面的 validator 处理逗号分隔字符串
NoDecodeList = _Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    app_name: str = "EnvAI"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    payment_provider: str = "mock"
    allowed_hosts: NoDecodeList = ["localhost", "127.0.0.1"]
    docs_enabled: bool = True
    trusted_proxy_headers: bool = False
    login_rate_limit: int = Field(default=10, ge=1, le=1000)
    api_rate_limit: int = Field(default=120, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    request_id_header: str = "X-Request-ID"

    # Secret / JWT（必须通过环境变量提供，勿提交）
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # 数据库
    database_url: str
    redis_url: str | None = None
    redis_password: str | None = None
    # Docker Compose 中仅覆盖主机与端口，凭据仍完全由 DATABASE_URL 提供。
    database_host_override: str | None = None
    database_port_override: int | None = Field(default=None, ge=1, le=65535)
    # Compose 与 PostgreSQL 容器共用这一组变量，避免容器内凭据漂移。
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None

    # 文件存储（Phase 1 本地存储；预留 MinIO/OSS/COS 切换）
    storage_backend: str = "local"
    local_storage_dir: str = "uploads"
    max_upload_file_size_mb: int = Field(default=20, ge=1, le=1024)
    max_upload_files_per_request: int = Field(default=10, ge=1, le=100)

    # 文档解析限制：避免不可信文件耗尽内存或数据库存储。
    max_pdf_pages: int = Field(default=500, ge=1, le=10_000)
    scanned_pdf_min_text_chars: int = Field(default=100, ge=0, le=100_000)
    max_docx_paragraphs: int = Field(default=100_000, ge=1, le=1_000_000)
    max_table_count: int = Field(default=1_000, ge=1, le=10_000)
    max_table_rows: int = Field(default=10_000, ge=1, le=1_000_000)
    max_excel_sheets: int = Field(default=20, ge=1, le=1_000)
    max_excel_rows: int = Field(default=10_000, ge=1, le=1_000_000)
    max_excel_columns: int = Field(default=200, ge=1, le=100_000)
    max_excel_cells: int = Field(default=2_000_000, ge=1_000, le=50_000_000)
    max_archive_uncompressed_size_mb: int = Field(default=100, ge=1, le=10_240)
    max_plain_text_chars: int = Field(default=5_000_000, ge=1_000, le=100_000_000)
    max_image_pixels: int = Field(default=100_000_000, ge=1_000_000, le=1_000_000_000)

    # Phase 3 AI Provider；默认 Mock，不会发起外部请求。
    ai_provider: str = "mock"
    ai_base_url: str | None = None
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None
    ai_timeout: float = Field(default=30.0, gt=0, le=300)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    # Some OpenAI-compatible gateways return an empty JSON object when
    # response_format=json_object is sent. The prompt still requires JSON,
    # and the provider parser accepts fenced JSON when this switch is disabled.
    ai_json_mode: bool = True

    # Phase 4 knowledge base / embedding. 默认使用本地确定性 Mock，不依赖外部服务。
    embedding_provider: str = "mock"
    embedding_model: str = "mock-hash-v1"
    embedding_base_url: str | None = None
    embedding_api_key: SecretStr | None = None
    embedding_dimension: int = Field(default=64, ge=8, le=4096)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    embedding_timeout: float = Field(default=30.0, gt=0, le=300)
    embedding_max_retries: int = Field(default=2, ge=0, le=5)
    chunk_target_tokens: int = Field(default=420, ge=50, le=4000)
    chunk_max_tokens: int = Field(default=600, ge=80, le=8000)
    chunk_overlap_tokens: int = Field(default=40, ge=0, le=500)
    search_vector_top_k: int = Field(default=30, ge=1, le=200)
    search_keyword_top_k: int = Field(default=30, ge=1, le=200)
    search_final_top_k: int = Field(default=10, ge=1, le=100)
    generation_max_concurrency: int = Field(default=3, ge=1, le=10)
    generation_stale_minutes: int = Field(default=30, ge=1, le=1440)
    invitation_expires_hours: int = Field(default=72, ge=1, le=720)

    # Phase 8: local, deterministic report export. PDF remains optional: a
    # failed converter must never discard a successfully rendered DOCX.
    export_temp_dir: str = f"{tempfile.gettempdir()}/envai-export"
    pdf_conversion_timeout: int = Field(default=90, ge=5, le=600)
    max_report_template_size_mb: int = Field(default=20, ge=1, le=100)

    # CORS
    cors_origins: NoDecodeList = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def sqlalchemy_database_url(self) -> str:
        """返回当前运行环境使用的数据库地址。"""
        # 纯本地运行尊重 DATABASE_URL；只有容器显式覆盖网络位置时才重组连接。
        if self.database_host_override or self.database_port_override:
            overrides: dict[str, str | int] = {}
            if self.postgres_user and self.postgres_password and self.postgres_db:
                overrides.update(
                    username=self.postgres_user,
                    password=self.postgres_password,
                    database=self.postgres_db,
                )
            if self.database_host_override:
                overrides["host"] = self.database_host_override
            if self.database_port_override:
                overrides["port"] = self.database_port_override
            # URL.__str__ masks passwords by default; feeding that masked URL
            # back to SQLAlchemy causes Docker connections to authenticate as
            # the literal password "***". Render explicitly for the engine.
            return make_url(self.database_url).set(**overrides).render_as_string(hide_password=False)
        return self.database_url

    @property
    def max_upload_file_size_bytes(self) -> int:
        return self.max_upload_file_size_mb * 1024 * 1024


settings = Settings()
