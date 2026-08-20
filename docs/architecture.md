# EnvAI 架构说明（Phase 1）

## 总体结构

```
用户 → 认证(JWT) → 项目管理 → 企业资料 → 项目文件 → Document Parsing → Structured Extraction → 后续(知识库/RAG/AI写作/文档生成)
```

## 后端分层

- `api/`        HTTP 路由与依赖注入
- `core/`       配置、安全、异常定义
- `models/`     SQLAlchemy ORM 模型
- `schemas/`    Pydantic 请求/响应模型
- `services/`   业务逻辑
- `repositories/` 数据访问封装（Phase 1 保持轻量）
- `db/`         Session / Base 管理
- `utils/`      日志等通用工具

## 统一响应格式

所有接口返回：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

`code` 非 0 表示业务错误，`message` 为人类可读信息。

## 第一批数据模型

- `User`          注册用户（预留企业/团队/角色扩展位）
- `Project`       环保咨询项目（环评/应急预案/风险评估等）
- `CompanyProfile` 企业资料（基本信息/生产信息/原辅材料 JSONB/污染治理信息）
- `ProjectFile`   项目上传文件（状态机：uploaded→parsing→parsed/failed）
- `ParsedDocument` 文件解析结果（一对一；状态机：pending→parsing→parsed/failed）

原辅材料在 Phase 1 以 JSONB 存储，Phase 3 企业数据结构化阶段再拆分规范表。

数据完整性约束：项目类型和状态均由数据库约束；每个项目至多一份企业资料。项目附件仅允许受认证且拥有该项目的用户下载或删除；上传支持一次最多 10 个、每个最多 20 MB（可由环境变量调整）。

## Phase 2 文档解析

`app/services/document_parser/` 提供统一 `BaseDocumentParser` 与 `ParserRegistry`，当前实现：

- `PDFParser`：PyMuPDF 提取页文本和 PDF metadata；无文本层时标记 `possible_scanned_pdf`。
- `DOCXParser`：python-docx 提取段落、样式、标题标记和表格行。
- `ExcelParser`：openpyxl 解析 XLSX，xlrd 解析 XLS，保留 Sheet、行、单元格类型和公式。
- `ImageParser`：Pillow 提取图片尺寸、格式、像素和文件大小；OCR 暂未启用。

解析结果保存到 `ParsedDocument.plain_text`、`structured_content` 和 `metadata`，其中 PDF 页码、Word 段落/表格索引、Excel Sheet/行位置均保留在结构化结果中，为下一阶段分块和来源追踪预留。

解析接口：

- `GET /api/v1/projects/{project_id}/files/{file_id}`
- `POST /api/v1/projects/{project_id}/files/{file_id}/parse`
- `GET /api/v1/projects/{project_id}/files/{file_id}/parse-status`
- `GET /api/v1/projects/{project_id}/files/{file_id}/parsed`
- `DELETE /api/v1/projects/{project_id}/files/{file_id}`

安全限制包括文件签名校验、路径归一化、上传大小限制、Office ZIP 解压体积限制、Excel Sheet/行/列/单元格限制、PDF 页数限制和图片像素限制。Phase 2 不接入大模型、RAG、Embedding、Redis、Celery 或重量级 OCR。

## Phase 3 企业信息结构化

Phase 3 保留 `CompanyProfile` 作为项目级基础资料，并新增 `Product`、`ProductionEquipment`、`RawMaterial`、`EnvironmentalFacility`。`ExtractionRun` 记录每次运行，`ExtractedFact` 保存原始值、标准化值、来源文件、页码/段落/表格/Sheet/Row、模型/Prompt 版本，`DataConflict` 保存不同来源的冲突，不自动覆盖人工确认数据。

当前抽取链路为：

```text
ParsedDocument → ExtractionPlanner → 规则/表格抽取 → Pydantic/Decimal/Unit 标准化
→ ExtractedFact → 去重 → Conflict Detection → 项目结构化数据 → 人工确认
```

默认 `AI_PROVIDER=mock`，不调用外部模型；后端已提供 OpenAI-Compatible Provider 抽象和结构化 JSON 校验边界。文档内容始终作为不可信 DATA 处理，不能改变系统指令；危险化学品判断、法规判断和缺失值补全不在本阶段执行。

Phase 3 API 包括：

- `POST /api/v1/projects/{project_id}/extract`
- `GET /api/v1/projects/{project_id}/extraction-status`
- `GET /api/v1/projects/{project_id}/extracted-data`
- `GET /api/v1/projects/{project_id}/extracted-facts`
- `GET /api/v1/projects/{project_id}/conflicts`
- `POST /api/v1/projects/{project_id}/extracted-facts/{fact_id}/accept|reject`
- `POST /api/v1/projects/{project_id}/conflicts/{conflict_id}/resolve`
- 产品、设备、原辅材料的修改与删除接口

## 后续演进（不在本期实现）

1. 文档解析（PDF/Word/Excel/OCR）
2. 企业数据结构化
3. 知识库（法规/标准/导则/模板/案例）
4. RAG（pgvector + embedding + reranker）
5. 模板化 AI 章节写作（可替换 AIProvider + Citation 可追溯）
6. 数据一致性校验（Validation Engine）
7. Word/PDF 自动生成（docxtpl + python-docx）
