# 数据库备份

每日执行 `POSTGRES_USER=... POSTGRES_DB=... ./scripts/backup_postgres.sh`，备份默认写入 `backups/postgres/`，脚本会检查非空、生成 SHA-256 并用 `pg_restore --list` 验证可读性。

保留策略建议：7 个日备份、4 个周备份、3 个月备份；备份目录必须使用磁盘加密或受控对象存储，普通平台管理员无权下载。

