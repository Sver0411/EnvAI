# Worker 恢复

当前项目尚未接入 Celery/RQ 等可靠任务队列；长任务仍由现有 FastAPI 服务调用，因此不能宣称具备 Worker crash recovery。上线前应将 extraction、generation、review、indexing、export 持久化到 Redis-backed queue，并增加任务幂等键、软/硬超时和 stale-run reconciler。

在队列迁移前，运维可定期执行 `python -m app.scripts.reconcile_stale_jobs --stale-after-minutes 30`，把超时仍处于进行中的生成、审核、索引和导出记录标记为失败；该操作绝不自动重跑或处理支付记录。
