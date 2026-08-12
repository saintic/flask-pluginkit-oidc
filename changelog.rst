Changelog
=========

v0.4.0
------

- 新特性：支持将 OAuth state 存储到 Redis 服务端（`PASSPORTD_OIDC_STATE_STORE=redis`），规避浏览器阻止跨站 Cookie 导致 state 丢失的问题
- 修复：`/authorized` 回调捕获 `MismatchingStateError`，state 校验失败时重定向回登录页，不再返回 500
- 变更：Redis 相关配置由 `PASSPORTD_OIDC_STATE_REDIS(_URL)` 更名为 `PASSPORTD_OIDC_REDIS(_URL)`
