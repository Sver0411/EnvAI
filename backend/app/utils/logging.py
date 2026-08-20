import logging
import json
import sys

from app.core.config import settings

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Small dependency-free structured formatter for container logs."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {"timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "level": record.levelname,
                   "service": "envai", "event": record.getMessage(), "logger": record.name}
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """统一日志配置（仅执行一次）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = logging.DEBUG if settings.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
