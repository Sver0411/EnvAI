# EnvAI 🌱

> An AI-assisted document production workspace for environmental consulting teams.

[中文文档](README.zh-CN.md) · [Architecture](docs/architecture.md) · [Real AI setup](docs/real-ai-setup.md) · [Production checklist](docs/production-readiness-checklist.md)

[![CI](https://github.com/Sver0411/EnvAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Sver0411/EnvAI/actions/workflows/ci.yml)

EnvAI turns company-provided environmental information, source files, professional references, and document templates into traceable consulting drafts. It combines structured extraction, a tenant-aware knowledge base, hybrid RAG retrieval, AI-assisted chapter writing, professional review, and Word/PDF export in one local-first SaaS workspace.

> **Status:** active MVP / local development. The repository contains the Phase 1–10 foundation, including multi-tenant workspaces, document generation, export, platform-operation foundations, and CI checks. Production deployment still requires the hardening items in the production checklist.

## Highlights

- 📁 Environmental impact assessment, emergency plan, risk assessment, and other consulting projects.
- 📄 PDF, DOCX, XLSX, and supported image-file parsing with source positions and metadata.
- 🧩 Structured extraction of company profiles, products, equipment, raw materials, environmental facilities, facts, conflicts, and provenance.
- 📚 Private or system knowledge bases for regulations, standards, technical guidelines, internal references, and case materials.
- 🔎 Keyword + vector retrieval with original source chunks available for citation.
- ✍️ Evidence-linked chapter drafting with an OpenAI-compatible chat model, project facts, uploaded materials, and knowledge sources.
- ✅ Preflight, consistency, citation, and professional quality checks before export.
- 📝 Draft editing, approval, versioning, and locking without overwriting reviewed content.
- 📦 Immutable report snapshots exported to DOCX/PDF with citations, figures, validation, hashes, and audit records.
- 🏢 Organization workspaces, member roles, project access, usage events, quotas, and tenant-isolation foundations.
- 🛠️ Platform-operation foundations for organizations, plans, usage analytics, announcements, billing foundations, and AI cost visibility.

## End-to-end workflow

~~~text
Register / sign in
        ↓
Create a project and select a report type
        ↓
Upload company files (PDF / Word / Excel)
        ↓
Parse → extract structured facts → resolve conflicts → confirm facts
        ↓
Upload and index professional references in a knowledge base
        ↓
Run readiness checks and generate an evidence-linked draft
        ↓
Edit → consistency check → professional review → approve / request changes
        ↓
Freeze a report snapshot → export Word / PDF → download an auditable artifact
~~~

AI output is a draft with evidence links. It does not replace professional review, signature, legal judgement, or regulatory submission.

## Architecture

~~~text
Vue 3 + TypeScript + Element Plus
                │
                │ REST / JSON (JWT + organization context)
                ▼
FastAPI ── Services ── SQLAlchemy / Alembic
   │             │                 │
   │             │                 ├─ PostgreSQL + pgvector
   │             │                 ├─ Local file storage
   │             │                 └─ DOCX / PDF export
   │             │
   │             ├─ Document parsers (PDF / DOCX / XLSX / image metadata)
   │             ├─ Structured extraction + conflict detection
   │             ├─ Knowledge indexing + hybrid retrieval
   │             ├─ OpenAI-compatible AI provider abstraction
   │             └─ Review, workflow, quota, audit, and billing foundations
   │
   └─ /health, /metrics, OpenAPI docs, request IDs, rate-limit hooks
~~~

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router, Axios |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic |
| Data | PostgreSQL 16, pgvector 0.8.x, JSONB, local file storage |
| Documents | PyMuPDF, python-docx, docxtpl, openpyxl, xlrd, Pillow |
| AI | OpenAI-compatible chat and embedding endpoints; Mock providers for tests/local boot |
| Quality | pytest, vue-tsc, Vite build, GitHub Actions, pip-audit, Bandit |

## Repository layout

~~~text
EnvAI/
├── backend/                 # FastAPI app, domain services, migrations, tests
│   ├── app/api/v1/          # Auth, projects, knowledge, generation, review, export, admin APIs
│   ├── app/models/          # SQLAlchemy models
│   ├── app/services/        # Parsing, extraction, RAG, AI, workflow, export, authorization
│   ├── alembic/             # Database migrations
│   └── tests/               # Backend tests
├── frontend/                # Vue application
├── demo_assets/             # Safe local demo documents
├── docs/                    # Architecture, security, deployment, runbooks, evaluation
├── docker/                  # Docker image definitions
├── evaluation/              # Evaluation fixtures and reports
├── scripts/                 # Demo data, evaluation, backup, and restore utilities
├── docker-compose.yml       # Optional local container stack
└── README.zh-CN.md          # Full Chinese documentation
~~~

## Requirements

- macOS, Linux, or Windows with a POSIX-compatible shell
- Python 3.11+
- Node.js 20+ (CI uses Node.js 22)
- PostgreSQL 16 with the vector extension for real vector search
- npm
- Optional: Docker Desktop for PostgreSQL or the complete container stack
- Optional: Ollama or another OpenAI-compatible AI gateway

## Local development (recommended)

The application can run locally without packaging the application into Docker. Only PostgreSQL is required for the normal local workflow.

### 1. Clone and configure

~~~bash
git clone https://github.com/Sver0411/EnvAI.git
cd EnvAI
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
~~~

Edit backend/.env:

~~~env
SECRET_KEY=replace-with-a-random-secret-at-least-32-characters
POSTGRES_USER=envai
POSTGRES_PASSWORD=choose-a-local-password
POSTGRES_DB=envai
DATABASE_URL=postgresql+psycopg://envai:choose-a-local-password@localhost:5433/envai
~~~

Never commit .env files, API keys, database passwords, uploaded files, or production certificates.

### 2. Start PostgreSQL

Use local PostgreSQL 16 + pgvector, or start only the database service with Docker:

~~~bash
docker compose up -d postgres
~~~

The development Compose file maps PostgreSQL to localhost:5433.

### 3. Install and start the backend

~~~bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
~~~

Windows activation: .venv\Scripts\activate

Backend endpoints:

- API: http://localhost:8000/api/v1
- OpenAPI UI: http://localhost:8000/docs
- Liveness: http://localhost:8000/health/live
- Readiness: http://localhost:8000/health/ready

### 4. Install and start the frontend

In a second terminal:

~~~bash
cd frontend
npm install
npm run dev
~~~

Open http://localhost:5173, register a local account, create a workspace/project, and follow the workflow.

### 5. Optional demo assets

Safe demonstration materials are included in demo_assets. Regenerate sample DOCX files with:

~~~bash
python scripts/create_demo_source_docs.py
~~~

The full seed script expects a prepared local database, demo user, and project. Review its constants before running:

~~~bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python ../scripts/seed_demo_full_flow.py
~~~

## Connect a real AI model

EnvAI starts with deterministic Mock providers so the UI, tests, parsing, and workflow can run without external credentials. Real generation uses an OpenAI-compatible chat-completions endpoint:

~~~env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-gateway.example/v1
AI_API_KEY=REPLACE_WITH_YOUR_AI_API_KEY
AI_MODEL=your-chat-model
AI_TIMEOUT=60
AI_MAX_RETRIES=2
AI_JSON_MODE=false
~~~

Set AI_JSON_MODE=false for gateways that do not reliably implement response_format. The provider is used for structured extraction, chapter drafting, and AI-assisted review; deterministic validation and authorization remain in the backend.

### Real embeddings for RAG

~~~env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-embedding-gateway.example/v1
EMBEDDING_API_KEY=REPLACE_WITH_YOUR_EMBEDDING_API_KEY
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=32
~~~

For a local no-cloud option:

~~~bash
ollama pull bge-m3
~~~

~~~env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDING_API_KEY=LOCAL_ONLY_PLACEHOLDER
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSION=1024
~~~

After changing embedding models, re-process existing knowledge documents. The configured dimension must exactly match the model output. See docs/real-ai-setup.md for details.

## Testing and quality

~~~bash
cd backend
source .venv/bin/activate
pytest -q
~~~

~~~bash
cd frontend
npm run build
~~~

Also run git diff --check. CI runs backend tests and migrations, frontend build, dependency audit, and Bandit security checks. See .github/workflows/ci.yml and docs/acceptance-plan.md.

## Optional full Docker stack

Docker is optional for local development. To run the complete stack:

~~~bash
cp backend/.env.example backend/.env
docker compose up -d --build
~~~

The Compose frontend is served on http://localhost:8080, the API on http://localhost:8000, and PostgreSQL on localhost:5433. For production-like deployment, read docs/deployment/production.md; do not treat development Compose as a production security boundary.

## Security and data boundaries

- JWT authentication and organization context protect private APIs.
- Project, file, document, knowledge-base, export, and usage access is checked against the current user and organization.
- Uploaded files stay outside Git and are subject to size, path, parser, archive, spreadsheet, and image limits.
- Logs avoid passwords, JWTs, API keys, cookies, full prompts, document bodies, and complete reports.
- Platform administrators see operational metadata by default, not customer report bodies or private files. Future support access must be explicit and auditable.
- Backups contain business data and vectors and must be encrypted and access-controlled.

Read docs/data-handling.md, docs/security/threat-model.md, and docs/runbooks/ before operating a shared environment.

## Current limitations

- No WeChat Pay, Alipay, Stripe, automatic invoicing, tax ERP, bank settlement, or commission system.
- No automatic regulatory submission or electronic-signature workflow.
- AI generation, parsing, review, and export are request-oriented services; durable workers/queues remain a production hardening item.
- OCR for scanned PDFs is not enabled by default.
- Mock AI, Mock embeddings, and Mock payment are for development/testing only.

## Documentation map

- [Architecture](docs/architecture.md)
- [Real AI and embeddings](docs/real-ai-setup.md)
- [Data handling](docs/data-handling.md)
- [Threat model](docs/security/threat-model.md)
- [Production deployment](docs/deployment/production.md)
- [Production readiness checklist](docs/production-readiness-checklist.md)
- [Monitoring](docs/monitoring.md)
- [Backup](docs/runbooks/database-backup.md), [restore](docs/runbooks/database-restore.md), [migration](docs/runbooks/database-migration.md)
- [Evaluation plan](docs/acceptance-plan.md) and evaluation/

## Contributing

1. Create a focused branch.
2. Keep secrets and customer data out of commits.
3. Add or update tests for behavior changes.
4. Run backend tests, frontend build, and git diff --check.
5. Describe migration, security, and data-boundary impacts in the pull request.

## License

No open-source license has been declared yet. Until a license file is added, all rights remain with the repository owner.
