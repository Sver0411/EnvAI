# AI Provider 故障

AI provider 超时或 429 时，保留登录、项目查看、已生成报告查看和下载能力；新生成/审核应快速失败并记录 request id、provider、model 和错误摘要，不记录 prompt 或文档正文。Embedding 模型不可随意 fallback，避免向量空间混用。

