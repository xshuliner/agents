# 其他框架与相似规则选择

先读取框架配置、官方项目约定、依赖版本与相邻模块，再选择最相近的一组规则；只借鉴相同的架构边界。

| 发现的形态 | 优先参考 | 额外确认 |
| --- | --- | --- |
| Svelte/SvelteKit | Vue 的组件/响应式原则；Next 的路由/SSR 边界 | runes/store、load/action 及 server/client 模块规则 |
| Angular | Vue 的组件输入输出原则；Express 的边界分层 | DI、RxJS 订阅和模块/standalone 约定 |
| Remix | Next 的路由、loader/action 与服务端边界 | nested routes、表单与缓存语义 |
| Fastify/Koa/Hono/Nest | Express 的 HTTP 边界；Node 的生命周期 | 插件/DI、错误传播和 middleware/hook 顺序 |
| Astro | Next 的岛屿与服务端边界 | island hydration、content collection 和 adapter |

若无法可靠归类，只使用通用规则，遵从项目内已有模式，并在结果中说明未确定的框架假设。不要为了套规则而创建框架并不支持的目录、生命周期或抽象。
