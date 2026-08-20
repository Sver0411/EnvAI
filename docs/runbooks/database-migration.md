# 数据库迁移

流程：备份 → 在 staging 执行 `alembic upgrade head` → 检查 SQL/锁风险 → 维护窗口执行 → health check → 业务 smoke test。生产部署不要让每个 API 容器同时执行 migration；使用独立的一次性 migration service。

