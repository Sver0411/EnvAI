# EnvAI Threat Model（Phase 11）

主要威胁：跨租户项目/RAG 访问、恶意 PDF/DOCX/压缩包、AI 输出 XSS、Prompt Injection、后台管理员账号被盗、订单金额篡改、上传路径穿越、Provider API Key 泄露和本地存储泄露。

现有缓解：后端组织/项目授权、后端计算订单金额、JWT + bcrypt、文件扩展名/MIME/签名/ZIP 条目校验、路径归一化、DOCX 模板宏拒绝、导出 subprocess 不使用 shell、平台后台不读取客户正文、生产配置 fail-closed。

已知缺口：没有 ClamAV、没有 TOTP MFA、没有持久 Redis 限流、没有可靠任务队列、没有对象存储签名 URL。上线前必须完成风险评审或明确书面接受风险。

