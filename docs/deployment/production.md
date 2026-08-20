# EnvAI 生产部署

当前推荐单机 Docker Compose：Nginx（HTTPS）→ Vue 静态站点 → FastAPI → PostgreSQL/pgvector；Redis 作为后续队列基础设施保留。当前代码没有 Celery/可靠后台 Worker，因此生成、解析、审核和导出仍需在迁移到正式任务队列前评估长请求风险。

## 部署顺序

1. 准备 Docker、域名和 TLS 证书，证书放在 `deploy/tls/`，不提交 Git。
2. 复制 `.env.production.example` 为 `.env.production`，填入随机 `SECRET_KEY`、数据库密码和正式 CORS/Host。
3. 执行 `docker compose -f docker-compose.production.yml config` 检查配置。
4. 先运行 migration service，再启动 API/frontend：`docker compose -f docker-compose.production.yml up -d postgres redis migration`，确认 migration 成功后启动其余服务。
5. 检查 `/health/live`、`/health/ready`，再执行登录和小文件上传 smoke test。

生产配置会拒绝 DEBUG、弱密钥、Mock Payment、通配 CORS 和 SQLite。数据库、Redis 不映射公网端口；上传文件使用独立 volume，容器以非 root 用户运行。

