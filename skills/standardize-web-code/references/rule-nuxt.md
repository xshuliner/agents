# Nuxt 规则

- 保持 `pages/`、`layouts/`、`components/`、`composables/`、`plugins/`、`middleware/`、`server/` 的自动扫描约定；不要把路由或自动导入迁移成手工结构。
- 区分 route middleware、server middleware 与 Nitro API handler。服务端处理器负责协议，业务逻辑保留在独立用例层。
- 为 `useAsyncData`/`useFetch` 保持稳定且有业务含义的 key，审查 SSR、缓存、刷新、懒加载和错误语义；不要让同 key 承载不同请求。
- 自动导入的重命名先检查扫描规则、命名冲突与显式导入调用方。插件注入使用稳定、具名、可类型化的键。
- 私密配置只能经 server runtime config 使用；客户端只能访问 `public` 配置。不要把密钥、数据库或 Node-only 依赖带入客户端包。
