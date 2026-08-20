# Phase 11 Architecture Inventory

| Component | Actual state |
|---|---|
| Frontend | Vue 3 + TypeScript, Vite production build, Nginx static serving |
| API | FastAPI + Uvicorn, SQLAlchemy/Alembic |
| Database | PostgreSQL 16 + pgvector image |
| Queue / Worker | Not implemented; no Celery, Redis queue or persistent worker exists |
| Redis | Not used by application; production Compose reserves an authenticated Redis service for a future queue/rate limiter |
| Storage | Local filesystem only; storage abstraction exists but MinIO/OSS/S3 implementation does not |
| Export | DOCX in process; optional LibreOffice subprocess with timeout and no shell invocation |
| Reverse proxy | Nginx development and HTTPS production configurations supplied |
| Monitoring | Request ID, JSON logs, health endpoints and `/metrics`; Prometheus/Grafana/alert delivery are not deployed |
| Billing | Mock payment is development/test only; production config rejects it |

This inventory deliberately distinguishes implemented runtime components from production targets so runbooks and readiness decisions do not assume nonexistent workers or monitoring infrastructure.

