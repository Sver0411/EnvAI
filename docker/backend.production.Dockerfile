FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app
COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/scripts ./scripts
RUN chmod +x scripts/start.sh && mkdir -p /app/uploads /tmp/envai-export && chown -R app:app /app /tmp/envai-export
USER app
EXPOSE 8000
CMD ["./scripts/start.sh"]
