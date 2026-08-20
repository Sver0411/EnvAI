# 数据库恢复

恢复前停止写入并创建隔离目标数据库。校验 `.sha256` 后执行：

```bash
CONFIRM_RESTORE=YES BACKUP_FILE=backups/postgres/envai_YYYY...dump \
POSTGRES_USER=envai POSTGRES_DB=envai_restore ./scripts/restore_postgres.sh
```

恢复后运行 `alembic current`、`SELECT count(*)` 检查 users/organizations/projects/knowledge_documents/report_snapshots，并执行健康检查、租户隔离测试和向量检索测试。数据库 downgrade 不等同于应用 rollback，必须先评估 migration 是否可逆。

