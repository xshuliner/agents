# Next.js 规则

- 先确认 App Router 或 Pages Router；遵守当前路由模式，不混用其数据获取和文件命名心智。保留 `page`、`layout`、`loading`、`error`、`not-found`、`route` 等约定文件名。
- App Router 默认 Server Component；仅在浏览器 API、交互状态或客户端 Hook 必需时添加 `'use client'`，并把客户端边界压缩到最小。
- Server Action 与 Route Handler 都要验证输入、执行授权并明确错误/缓存语义；Route Handler 处理 HTTP，领域用例下沉到独立模块。
- 审查 `fetch`、`revalidate`、`dynamic` 与缓存失效策略是否匹配实时性。客户端模块不可导入密钥、数据库或 server-only 依赖。
