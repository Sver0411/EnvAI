# EnvAI 真实 AI 文档生产配置

EnvAI 默认使用 `mock` Provider，便于本地开发和自动化测试。真实环境应通过
OpenAI-compatible 接口接入模型，接口可以是云端服务，也可以是内网 Ollama/vLLM
网关。API Key 只写入本地 `backend/.env` 或生产密钥管理系统，不要提交到 Git。

## 1. 配置 LLM

在 `backend/.env` 中设置：

```env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-llm-endpoint.example/v1
AI_API_KEY=replace-with-secret
AI_MODEL=your-chat-model
AI_TIMEOUT=60
AI_MAX_RETRIES=2
# OpenCode Go + DeepSeek V4 Flash: set false for gateway compatibility.
AI_JSON_MODE=false
```

模型需要支持 `POST /chat/completions`，并尽量支持
`response_format: {"type": "json_object"}`。生成、结构化抽取和 AI 辅助审核共用
该 Provider；规则抽取和事实审核不会被绕过。

## 2. 配置 Embedding

真实 RAG 还需要 Embedding 接口：

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-embedding-endpoint.example/v1
EMBEDDING_API_KEY=replace-with-secret
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=32
```

`EMBEDDING_DIMENSION` 必须与模型实际返回的向量维度一致。当前 Provider 调用
`POST /embeddings`，并对返回数量、顺序和维度做校验。

本地开发可以使用 Ollama 的开源 `bge-m3`，无需云端 API Key。本机直接运行
后端时：

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSION=1024
```

先执行 `ollama pull bge-m3`，再重新处理已有知识库文档。BGE-M3 的向量维度为
1024，不能与之前的 Mock 64 维向量混用。

如果使用 Docker Desktop 启动本地开发后端，Compose 会自动将地址切换为
`http://host.docker.internal:11434/v1`。

## 3. 重新索引知识库

切换 Embedding 后，旧的 Mock 向量不能直接复用。需要在知识库页面逐个执行
“重新处理”，或调用知识文档的 `POST /api/v1/knowledge-documents/{id}/process`。
索引完成后再开始生成报告。

## 4. 推荐生产流程

1. 上传目标企业的 PDF、DOCX、XLSX 等资料。
2. 执行项目抽取，检查企业概况、产品、设备、原辅材料和环保设施。
3. 人工确认或拒绝抽取事实，解决数据冲突。
4. 选择“环境影响评价报告（标准版）”或“突发环境事件应急预案（标准版）”。
5. 运行章节预检和批量生成。
6. 检查每章的企业事实、知识库引用、缺失信息和数字一致性。
7. 执行专业质量审核，人工修改并锁定章节后再导出 Word/PDF。

AI 只生成带证据链的草稿，不能替代环保专业人员的最终审查、签章或监管提交。
