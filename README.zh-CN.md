# EnvAI 🌱

> 面向环保咨询团队的 AI 辅助文档生产工作台。

[English README](README.md) · [架构说明](docs/architecture.md) · [真实 AI 配置](docs/real-ai-setup.md) · [生产检查清单](docs/production-readiness-checklist.md)

[![CI](https://github.com/Sver0411/EnvAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Sver0411/EnvAI/actions/workflows/ci.yml)
[![Docker Compose](https://img.shields.io/badge/docker--compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Nginx](https://img.shields.io/badge/nginx-reverse%20proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)

EnvAI 将目标企业资料、项目文件、专业依据和文档模板组织成可追溯的环保咨询文档生产流程。系统把企业信息结构化抽取、多租户知识库、RAG 检索、AI 章节写作、专业质量审查和 Word/PDF 导出整合到一个本地优先的 SaaS 工作台中。

## 项目状态

当前项目处于 **MVP / 本地开发阶段**。仓库包含 Phase 1–10 的基础能力，包括组织租户、项目与文档编制、知识库、AI 生成、报告导出、平台运营基础和 CI 检查。正式生产部署仍需完成[生产检查清单](docs/production-readiness-checklist.md)中的加固项目。

## 核心能力

- 📁 管理环境影响评价、突发环境事件应急预案、环境风险评估和其他环保咨询项目。
- 📄 上传 PDF、DOCX、XLSX 以及受支持的图片文件，解析正文并保留来源位置。
- 🧩 抽取企业概况、产品、设备、原辅材料、环保设施、事实、冲突和来源信息。
- 📚 创建私有或系统共享知识库，管理法规、标准、技术导则、内部资料和案例材料。
- 🔎 使用关键词 + 向量的混合检索，保留可直接引用的原始 Chunk。
- ✍️ 结合项目事实、企业资料、知识库依据和 OpenAI-compatible 聊天模型，生成带证据链的章节草稿。
- ✅ 执行生成前检查、一致性检查、引用检查和专业质量审查。
- 📝 编辑、审核、版本化并锁定章节，避免覆盖已审核内容。
- 📦 基于不可变报告快照导出 DOCX/PDF，包含引用、图表、校验、哈希和审计记录。
- 🏢 通过组织上下文、成员角色、权限、用量事件和配额隔离不同企业的数据。
- 🛠️ 提供平台后台基础，用于组织、套餐、用量、公告、账单基础和 AI 成本运营分析。

## 全流程

~~~text
注册 / 登录
   ↓
新建项目并选择报告类型
   ↓
上传企业资料（PDF / Word / Excel）
   ↓
解析 → 抽取结构化事实 → 处理冲突 → 人工确认
   ↓
上传并索引法规、标准、导则或案例资料
   ↓
执行章节资料检查，生成带证据引用的初稿
   ↓
编辑 → 一致性检查 → 专业审查 → 审核通过 / 标记修改
   ↓
冻结报告快照 → 导出 Word / PDF → 下载可审计文件
~~~

AI 只负责生成带依据的草稿，不能替代环保专业人员的最终审核、签章、法律判断或监管提交。

## 系统架构

~~~text
Vue 3 + TypeScript + Element Plus
                │
                │ REST / JSON（JWT + 组织上下文）
                ▼
FastAPI ── 业务服务 ── SQLAlchemy / Alembic
   │             │                 │
   │             │                 ├─ PostgreSQL + pgvector
   │             │                 ├─ 本地文件存储
   │             │                 └─ DOCX / PDF 导出
   │             │
   │             ├─ 文档解析（PDF / DOCX / XLSX / 图片元数据）
   │             ├─ 结构化抽取与冲突检测
   │             ├─ 知识库索引与混合检索
   │             ├─ OpenAI-compatible AI Provider 抽象
   │             └─ 审核、工作流、配额、审计和商业化基础
   │
   └─ /health、/metrics、OpenAPI 文档、Request ID、限流钩子
~~~

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Axios |
| 后端 | Python 3.11+、FastAPI、SQLAlchemy 2、Pydantic 2、Alembic |
| 数据 | PostgreSQL 16、pgvector 0.8.x、JSONB、本地文件存储 |
| 文档 | PyMuPDF、python-docx、docxtpl、openpyxl、xlrd、Pillow |
| AI | OpenAI-compatible 聊天和 Embedding 接口；Mock Provider 用于测试和本地启动 |
| 质量 | pytest、vue-tsc、Vite build、GitHub Actions、pip-audit、Bandit |

## 目录结构

~~~text
EnvAI/
├── backend/                 # FastAPI 后端、领域服务、迁移和测试
│   ├── app/api/v1/          # 认证、项目、知识库、生成、审查、导出、后台 API
│   ├── app/models/          # SQLAlchemy 数据模型
│   ├── app/services/        # 解析、抽取、RAG、AI、工作流、导出、权限服务
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 后端测试
├── frontend/                # Vue 前端应用
├── demo_assets/             # 安全的本地演示资料
├── docs/                    # 架构、安全、部署、运维手册和评测文档
├── docker/                  # Docker 镜像定义
├── evaluation/              # 评测数据和报告
├── scripts/                 # 演示数据、评测、备份和恢复脚本
├── docker-compose.yml       # 可选的本地容器编排
└── README.md                # 默认英文文档
~~~

## 环境要求

- macOS、Linux 或 Windows + POSIX 兼容 Shell
- Python 3.11 或更高版本
- Node.js 20+（CI 使用 Node.js 22）
- PostgreSQL 16，并启用 vector 扩展以使用真实向量检索
- npm
- 可选：Docker Desktop，用于启动 PostgreSQL 或完整容器栈
- 可选：Ollama，或任意 OpenAI-compatible AI 网关

## 本地开发（推荐）

应用可以完全在本地运行，不要求把应用打包进 Docker。正常本地开发只需要 PostgreSQL。

### 1. 克隆并创建配置

~~~bash
git clone https://github.com/Sver0411/EnvAI.git
cd EnvAI
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
~~~

编辑 backend/.env：

~~~env
SECRET_KEY=替换为至少32字符的随机密钥
POSTGRES_USER=envai
POSTGRES_PASSWORD=设置本地数据库密码
POSTGRES_DB=envai
DATABASE_URL=postgresql+psycopg://envai:设置本地数据库密码@localhost:5433/envai
~~~

不要把 .env、API Key、数据库密码、上传文件或生产证书提交到 Git。

### 2. 启动 PostgreSQL

可以使用本机 PostgreSQL 16 + pgvector，也可以只用 Docker 启动数据库：

~~~bash
docker compose up -d postgres
~~~

开发 Compose 会将数据库映射到 localhost:5433。

### 3. 安装并启动后端

~~~bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
~~~

Windows 激活：.venv\Scripts\activate

后端地址：

- API：http://localhost:8000/api/v1
- OpenAPI：http://localhost:8000/docs
- 存活检查：http://localhost:8000/health/live
- 就绪检查：http://localhost:8000/health/ready

### 4. 安装并启动前端

另开终端：

~~~bash
cd frontend
npm install
npm run dev
~~~

打开 http://localhost:5173，注册本地账号、创建工作区和项目，即可按上面的流程使用。

### 5. 可选演示资料

仓库的 demo_assets/ 已包含安全演示资料，也可以重新生成演示 DOCX：

~~~bash
python scripts/create_demo_source_docs.py
~~~

完整种子脚本适用于已经准备好本地数据库、演示用户和项目的环境。运行前请检查脚本中的常量：

~~~bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python ../scripts/seed_demo_full_flow.py
~~~

## 接入真实 AI 模型

EnvAI 默认使用确定性的 Mock Provider，使界面、测试、解析和工作流无需外部密钥即可启动。真实生成使用 OpenAI-compatible 的 /chat/completions 接口：

~~~env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-gateway.example/v1
AI_API_KEY=REPLACE_WITH_YOUR_AI_API_KEY
AI_MODEL=你的聊天模型
AI_TIMEOUT=60
AI_MAX_RETRIES=2
AI_JSON_MODE=false
~~~

不支持或不稳定实现 response_format 的网关建议设置 AI_JSON_MODE=false。AI Provider 用于结构化抽取、章节草稿和 AI 辅助审查；确定性校验和权限控制始终由后端执行。

### 接入真实 Embedding

~~~env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-embedding-gateway.example/v1
EMBEDDING_API_KEY=REPLACE_WITH_YOUR_EMBEDDING_API_KEY
EMBEDDING_MODEL=你的 Embedding 模型
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=32
~~~

也可以使用本地 Ollama 的开源 bge-m3：

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

切换 Embedding 模型后，需要重新处理已有知识库资料；配置维度必须与模型实际输出完全一致。详细配置见 docs/real-ai-setup.md。

## 测试与质量检查

~~~bash
cd backend
source .venv/bin/activate
pytest -q
~~~

~~~bash
cd frontend
npm run build
~~~

另外执行 git diff --check。CI 会执行后端测试和迁移、前端构建、依赖审计和 Bandit 安全检查。详见 .github/workflows/ci.yml 和 docs/acceptance-plan.md。

## 可选完整 Docker 栈

Docker 不是本地开发必需项。如果需要一次启动完整容器栈：

~~~bash
cp backend/.env.example backend/.env
docker compose up -d --build
~~~

完整 Compose 前端地址为 http://localhost:8080，API 为 http://localhost:8000，PostgreSQL 为 localhost:5433。生产部署请阅读 docs/deployment/production.md，不要把开发 Compose 当作生产安全边界。

## 安全与数据边界

- 受保护 API 使用 JWT 认证和组织上下文。
- 项目、文件、文档、知识库、导出和用量访问都会检查当前用户与组织权限。
- 上传文件不进入 Git，并受文件大小、路径、解析器、压缩包、表格和图片像素限制。
- 日志不会记录密码、JWT、API Key、Cookie、完整 Prompt、文档正文或完整报告。
- 平台管理员默认只能查看运营元数据，不能查看客户报告正文、私有文件或私有知识库内容；未来 Support Access 必须显式授权并可审计。
- 备份包含业务数据和向量，必须加密并限制运维账号访问。

共享环境运行前，请阅读 docs/data-handling.md、docs/security/threat-model.md 和 docs/runbooks/。

## 当前限制

- 不包含微信支付、支付宝、Stripe、自动开票、税务 ERP、银行清算或分销返佣。
- 不包含自动监管提交和电子签章闭环。
- AI 生成、解析、审查和导出当前仍以请求服务为主，可靠 Worker/队列属于生产加固项。
- 默认不启用扫描 PDF OCR。
- Mock AI、Mock Embedding 和 Mock Payment 仅用于开发和测试。

## 文档索引

- [架构说明](docs/architecture.md)
- [真实 AI 与 Embedding](docs/real-ai-setup.md)
- [数据处理边界](docs/data-handling.md)
- [威胁模型](docs/security/threat-model.md)
- [生产部署](docs/deployment/production.md)
- [生产检查清单](docs/production-readiness-checklist.md)
- [监控](docs/monitoring.md)
- [数据库备份](docs/runbooks/database-backup.md)、[恢复](docs/runbooks/database-restore.md)、[迁移](docs/runbooks/database-migration.md)
- [验收计划](docs/acceptance-plan.md)和 evaluation/

## 参与贡献

1. 创建聚焦单一目标的分支。
2. 不提交密钥和客户数据。
3. 为行为变更补充或更新测试。
4. 执行后端测试、前端构建和 git diff --check。
5. 在 Pull Request 中说明迁移、安全和数据边界影响。

## License

当前仓库尚未声明开源许可证。在添加 LICENSE 文件之前，所有权利归仓库所有者保留。
