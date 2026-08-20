# Production Readiness Checklist

- [ ] 生产随机密钥、独立数据库密码、非 Mock Payment
- [ ] 正式域名、HTTPS 证书、CORS/Host 白名单
- [ ] PostgreSQL 每日备份、checksum、隔离恢复演练
- [ ] 上传文件备份与私有访问策略
- [ ] `/health/live`、`/health/ready` 和 request id 已验证
- [ ] API 5xx、磁盘、备份失败、队列积压有告警方案
- [ ] 登录和 API 限流已在 production-like 环境测试
- [ ] 租户隔离、Billing、上传、XSS 安全回归通过
- [ ] 可靠后台队列、病毒扫描、Platform Admin MFA 上线前补齐
- [ ] staging 与 production 数据隔离，未复制未脱敏客户文件

