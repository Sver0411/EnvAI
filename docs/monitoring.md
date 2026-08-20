# 监控与告警

API 提供低基数 Prometheus 文本指标 `/metrics`，包括请求总量、状态码计数和延迟总量/次数；不把 user_id、organization_id、project_id 放入指标标签。该 endpoint 应只通过内网或反向代理暴露给 Prometheus，不能公网开放。

当前 Compose 未部署 Prometheus/Grafana/告警服务，因此 Phase 11 不宣称已有可视化监控闭环。上线时至少配置以下告警：API 5xx 比例、`/health/ready` 失败、PostgreSQL/Redis 不可用、磁盘使用率、备份失败、容器反复重启，以及 AI Provider 失败/429。备份失败和磁盘告警必须有实际通知渠道。

