---
name: standardize-web-code
description: 识别 Web、Node 与全栈项目的框架和既有约定，并统一 JavaScript/TypeScript 的命名、模块归属、组件与状态、类型、接口、安全、无障碍和验证方式。用于创建、修改、重构、评审或治理 Vue、Nuxt、React、Next.js、Node.js、Express 及相近项目，尤其适用于建立或执行可维护、可验证且符合高质量工程实践的团队开发规范。
---

# Web 代码规范化

遵守优先级：安全与正确性、公开契约、仓库规则和框架约定，最后才是本 Skill。以降低维护者理解、定位和安全修改代码的心智负担为目标；保留用户已有无关改动。

## 识别项目

编辑前依次检查最近的 `AGENTS.md`、`package.json`、锁文件、框架配置、目录约定、Lint/格式化/类型检查配置、CI 工作流、目标模块及其调用方和测试。不要只依赖一个目录名或依赖名称。

按以下证据识别并加载规则；全栈项目可同时加载前端和服务端规则。

| 优先识别 | 典型证据 | 读取规则 |
| --- | --- | --- |
| Nuxt | `nuxt.config.*` 或 `nuxt` 依赖 | [rule-nuxt.md](references/rule-nuxt.md) |
| Next.js | `next.config.*`、`app/`/`pages/` 路由或 `next` 依赖 | [rule-next.md](references/rule-next.md) |
| Vue | `.vue` 文件、`vite.config.*` 的 Vue 插件或 `vue` 依赖 | [rule-vue.md](references/rule-vue.md) |
| React | JSX/TSX、React 插件或 `react` 依赖 | [rule-react.md](references/rule-react.md) |
| Express | `express` 依赖、Router/Controller 入口 | [rule-express.md](references/rule-express.md) |
| Node.js | Node 入口、CLI、Worker 或服务端代码 | [rule-node.md](references/rule-node.md) |

若是其他框架，读取 [rule-other-frameworks.md](references/rule-other-frameworks.md)：从配置和相邻模块确定最接近的已列框架，只迁移相同的生命周期、路由和运行时规则；不要把名称相似的 API 当作行为相同。

每次均读取 [rule-common-workflow.md](references/rule-common-workflow.md) 与任务相关的通用规则：

- 命名或重命名： [rule-common-naming.md](references/rule-common-naming.md)
- 文件、组件、抽象或状态： [rule-common-code-organization.md](references/rule-common-code-organization.md)
- 前端样式或 Tailwind： [rule-common-styling.md](references/rule-common-styling.md)
- TypeScript、类型迁移、数据模型或错误状态： [rule-common-types.md](references/rule-common-types.md)
- API、数据、配置、安全、无障碍、删除、测试或验证： [rule-common-quality.md](references/rule-common-quality.md)

## 执行

1. 先说明识别出的框架、运行时与路由/渲染边界，以及将遵循的现有工具链；证据不足时采用最保守的相近规则并明确假设。
2. 围绕一个业务流程组织输入、真实状态、派生值、副作用、数据访问和输出；用同一领域词贯穿代码、测试和契约。
3. 优先让本地业务路径直读可懂；只在稳定复用、领域不变量、外部边界或独立复杂度成立时抽象。不要为压缩文件长度或预想复用而拆分。
4. 修改契约或删除代码前，搜索静态和动态引用、生成/扫描入口、序列化与持久化键；删除已证实无用的实现、导出、依赖与样式，不保留“或许以后会用”的死代码。未经明确授权不得破坏兼容性。
5. 按风险运行仓库已有的格式化、Lint、类型检查、聚焦测试和必要构建，并审计最终 Diff。安全、权限、缓存、并发、迁移或无障碍相关变更要补充相应验证。只如实报告执行过的结果。

## 完成标准

- 运行时边界、领域词汇和文件归属清晰一致。
- 同一功能的文件、目录、导出和测试可通过一致的领域前缀直接定位；阅读一个用例不需要跨越无意义的包装层。
- 不引入无证据的目录模板、工具、设计模式或框架习惯。
- 导入导出、路由、测试、样式和公开契约随重命名或删除同步更新。
- 变更通过适用验证，或明确列出未运行项、风险与准确原因。
