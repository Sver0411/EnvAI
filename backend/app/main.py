import logging
import time
import uuid
import hashlib
from collections import Counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import ApiError, AuthError
from app.core.production import validate_production_config
from app.db.session import engine
from app.services.rate_limit import InMemoryRateLimiter
from app.schemas.common import Resp
from app.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
validate_production_config(settings)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

_rate_limiter = InMemoryRateLimiter()
_metrics = Counter()
_latency_total = 0.0
_latency_count = 0


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request.state.started_at = time.perf_counter()
    request_id = request.headers.get(settings.request_id_header, "")[:128] or str(uuid.uuid4())
    request.state.request_id = request_id
    if settings.environment == "production":
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        allowed = {item.lower() for item in settings.allowed_hosts}
        if allowed and host not in allowed and "*" not in allowed:
            return JSONResponse(status_code=400, content={"code": 400, "message": "非法 Host", "data": None}, headers={settings.request_id_header: request_id})
        limit = settings.login_rate_limit if request.url.path.endswith("/auth/login") else settings.api_rate_limit
        kind = "login" if request.url.path.endswith("/auth/login") else "api"
        ip = request.client.host if request.client else "unknown"
        token = request.headers.get("authorization", "")
        identities = [f"ip:{ip}:{kind}"]
        if token: identities.append(f"user:{hashlib.sha256(token.encode()).hexdigest()[:24]}:{kind}")
        organization = request.headers.get("x-organization-id")
        if organization: identities.append(f"organization:{organization}:{kind}")
        if not all(_rate_limiter.allow(key, limit, settings.rate_limit_window_seconds) for key in identities):
            return JSONResponse(status_code=429, content={"code": 429, "message": "RATE_LIMIT_EXCEEDED", "data": None}, headers={"Retry-After": str(settings.rate_limit_window_seconds), settings.request_id_header: request_id})
    response = await call_next(request)
    global _latency_total, _latency_count
    elapsed = max(0.0, time.perf_counter() - request.state.started_at) if hasattr(request.state, "started_at") else 0.0
    _metrics["http_requests_total"] += 1
    _metrics[f"http_response_status_total{{status=\"{response.status_code}\"}}"] += 1
    _latency_total += elapsed; _latency_count += 1
    response.headers[settings.request_id_header] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; frame-ancestors 'none'"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    logger.info("ApiError request_id=%s method=%s path=%s code=%s", getattr(request.state, "request_id", "-"), request.method, request.url.path, exc.code)
    return JSONResponse(
        status_code=200,
        content=Resp(code=exc.code, message=exc.message, data=exc.detail).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info("ValidationError request_id=%s method=%s path=%s", getattr(request.state, "request_id", "-"), request.method, request.url.path)
    return JSONResponse(
        status_code=200,
        content=Resp(code=422, message="参数校验失败", data=exc.errors()).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error request_id=%s method=%s path=%s", getattr(request.state, "request_id", "-"), request.method, request.url.path)
    return JSONResponse(
        status_code=200,
        content=Resp(code=500, message="服务器内部错误", data=None).model_dump(),
    )


@app.get("/health", tags=["system"])
def health() -> Resp[dict]:
    return Resp(data={"status": "ok", "version": settings.app_version})


@app.get("/health/live", tags=["system"])
def health_live() -> Resp[dict]:
    return Resp(data={"status": "ok", "version": settings.app_version})


@app.get("/health/ready", tags=["system"])
def health_ready() -> Resp[dict]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return Resp(code=503, message="数据库未就绪", data={"status": "not_ready", "database": "unavailable"})
    return Resp(data={"status": "ready", "database": "ok"})


@app.get("/health/dependencies", tags=["system"])
def health_dependencies() -> Resp[dict]:
    result: dict[str, str] = {}
    try:
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
        result["postgres"] = "ok"
    except Exception: result["postgres"] = "unavailable"
    result["redis"] = "not_configured"
    result["storage"] = "configured" if settings.storage_backend else "not_configured"
    result["ai_provider"] = settings.ai_provider
    if settings.ai_provider == "mock":
        result["ai"] = "mock"
    else:
        result["ai"] = "configured" if settings.ai_base_url and settings.ai_api_key and settings.ai_model else "misconfigured"
    result["embedding_provider"] = settings.embedding_provider
    if settings.embedding_provider == "mock":
        result["embedding"] = "mock"
    else:
        result["embedding"] = "configured" if settings.embedding_base_url and settings.embedding_api_key and settings.embedding_model else "misconfigured"
    return Resp(data=result)


@app.get("/version", tags=["system"])
def version() -> Resp[dict]:
    return Resp(data={"version": settings.app_version, "environment": settings.environment})


@app.get("/metrics", tags=["system"], response_class=PlainTextResponse)
def metrics() -> str:
    """Prometheus-compatible low-cardinality application counters."""
    lines = ["# HELP envai_http_requests_total HTTP requests handled", "# TYPE envai_http_requests_total counter",
             f"envai_http_requests_total {_metrics['http_requests_total']}",
             "# TYPE envai_http_response_status_total counter"]
    for key, value in sorted(_metrics.items()):
        if key.startswith("http_response_status_total"):
            lines.append(f"envai_{key} {value}")
    lines.extend(["# TYPE envai_http_request_duration_seconds_sum counter", f"envai_http_request_duration_seconds_sum {_latency_total:.6f}",
                  "# TYPE envai_http_request_duration_seconds_count counter", f"envai_http_request_duration_seconds_count {_latency_count}"])
    return "\n".join(lines) + "\n"


app.include_router(api_router, prefix="/api/v1")
