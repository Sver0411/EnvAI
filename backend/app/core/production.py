from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings


class ProductionConfigError(ValueError):
    """Raised before startup when an unsafe production configuration is used."""


@dataclass(frozen=True)
class ProductionConfigReport:
    environment: str
    warnings: tuple[str, ...] = ()


def validate_production_config(settings: Settings) -> ProductionConfigReport:
    """Fail closed for dangerous settings; development remains convenient."""
    if settings.environment != "production":
        return ProductionConfigReport(settings.environment)
    errors: list[str] = []
    warnings: list[str] = []
    secret = settings.secret_key.get_secret_value() if hasattr(settings.secret_key, "get_secret_value") else str(settings.secret_key)
    if settings.debug:
        errors.append("production 禁止 DEBUG=true")
    if len(secret) < 32 or secret.lower() in {"secret", "changeme", "change-me-in-production-please-use-a-long-random-secret"}:
        errors.append("production 必须使用高强度 SECRET_KEY")
    if settings.payment_provider == "mock":
        errors.append("production 禁止 PAYMENT_PROVIDER=mock")
    if settings.ai_provider == "mock":
        errors.append("production 禁止 AI_PROVIDER=mock")
    if settings.embedding_provider == "mock":
        errors.append("production 禁止 EMBEDDING_PROVIDER=mock")
    if not settings.cors_origins or "*" in settings.cors_origins:
        errors.append("production CORS_ORIGINS 不能是 * 或空值")
    if settings.docs_enabled:
        warnings.append("公网文档已开启，建议通过内网或反向代理保护")
    if settings.storage_backend == "local":
        warnings.append("production 仍使用本地存储，必须配置独立磁盘备份或迁移对象存储")
    if settings.redis_url and not settings.redis_password:
        errors.append("配置 Redis_URL 时必须同时提供 Redis 密码")
    if settings.redis_password and settings.redis_password.lower() in {"change_me", "changeme", "password"}:
        errors.append("production 禁止使用默认 Redis 密码")
    parsed = urlparse(settings.database_url)
    if parsed.scheme.startswith("sqlite"):
        errors.append("production 禁止使用 SQLite")
    if errors:
        raise ProductionConfigError("；".join(errors))
    return ProductionConfigReport(settings.environment, tuple(warnings))
