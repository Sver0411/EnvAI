# 文件存储备份

本地存储阶段使用 `./scripts/backup_storage.sh` 对 `uploads` 做压缩归档并生成 checksum（若直接在 backend 工作目录运行，可显式设置 `SOURCE_DIR=uploads`）。生产应迁移至私有 S3-compatible/OSS，并开启版本控制和生命周期策略。恢复时先校验 checksum，再恢复到隔离目录，确认 ProjectFile、KnowledgeDocument 和 ExportArtifact 路径一致。
