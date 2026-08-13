---
name: standardize-web-code
description: 识别 Web、Node.js 与全栈项目的真实框架、运行时和既有约定，并在创建、修改、重构、审查或治理 JavaScript/TypeScript 代码时，以最小必要改动统一命名、模块归属、组件与状态、类型、接口、安全、无障碍和验证。用于 Vue、Nuxt、React、Next.js、Vite、Node.js、Express 及相近项目；不用于 Cocos Creator、原生应用或非 Web 代码，除非任务同时明确涉及 Web/Node 边界。
---

# Web 代码规范化

遵守优先级：用户目标、安全与正确性、公开契约、仓库规则和框架约定，最后才是本 Skill。以降低维护者理解、定位和安全修改代码的心智负担为目标；优先小步、可验证、可审阅的变更，并保留用户已有无关改动。

## 识别项目

编辑前，先确定仓库根目录、当前工作区状态和任务实际影响的应用/包。Monorepo 中从根配置定位目标 workspace，再读取该 workspace 的脚本和配置；不要把根目录工具链、另一个应用或示例项目的约定套到目标模块。

按需检查最近的 `AGENTS.md`、`package.json`、锁文件、框架配置、目录约定、Lint/格式化/类型检查配置、CI 工作流、目标模块、调用方和测试。只读取能降低当前不确定性的证据，不要只依赖目录名或依赖名称，也不要为了规范化进行无关的全仓扫描。

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

每次读取 [rule-common-workflow.md](references/rule-common-workflow.md) 与 [rule-personal-preferences.md](references/rule-personal-preferences.md)。后者是可持续增补的个人默认偏好：与用户当前任务、仓库规则或无障碍/兼容性冲突时，按本 Skill 的优先级处理，并在结果中说明取舍。再只读取任务相关的通用规则：

- 命名或重命名： [rule-common-naming.md](references/rule-common-naming.md)
- 文件、组件、抽象或状态： [rule-common-code-organization.md](references/rule-common-code-organization.md)
- 前端样式或 Tailwind： [rule-common-styling.md](references/rule-common-styling.md)
- TypeScript、类型迁移、数据模型或错误状态： [rule-common-types.md](references/rule-common-types.md)
- API、数据、配置、安全、无障碍、删除、测试或验证： [rule-common-quality.md](references/rule-common-quality.md)

## 执行

1. 先用一句话说明识别出的框架、运行时、目标 workspace 与路由/渲染边界，以及将遵循的已有工具链。证据不足时采用最保守的相近规则，并明确假设。
2. 默认定位最小变更面：目标、调用链、测试和公开契约。只有任务或证据要求时，才扩展到跨模块重构、依赖升级或目录迁移；不要借修复顺带改写无关代码。用户明确要求“彻底重构”时，切换到彻底重构模式，按业务场景设计最优的整体实现，而非受现有内部结构、冗余包装或过期兼容层约束。
3. 围绕一个业务流程组织输入、真实状态、派生值、副作用、数据访问和输出；用同一领域词贯穿代码、测试和契约。优先让本地路径直读可懂，只在稳定复用、领域不变量、外部边界或独立复杂度成立时抽象。
4. 修改契约或删除代码前，搜索静态和动态引用、生成/扫描入口、序列化与持久化键；删除已证实无用的实现、导出、依赖与样式，不保留注释掉的实现或“以后可能用”的死代码。默认不破坏公开兼容性；在彻底重构模式中，移除不再服务当前业务的内部历史兼容代码，除非用户或仓库明确要求保留对外契约、迁移路径或旧数据兼容。
5. 先运行与变更紧邻的快速检查，再按风险扩大到仓库已有的格式化、Lint、类型检查、聚焦测试和必要构建。不要为了验证启动长期运行的开发服务，也不要以修复检查为由升级无关依赖。最后审计 `git diff --check`、工作区和最终 Diff；安全、权限、缓存、并发、迁移或无障碍相关变更补充相应验证。
6. 用简洁中文交付：说明改了什么、为什么、已运行的验证及结果；未运行项只列会影响交付判断的原因和风险。不得把建议、推测或未执行检查表述为完成事实。

## 完成标准

- 运行时边界、领域词汇和文件归属清晰一致。
- 同一功能的文件、目录、导出和测试可通过一致的领域前缀直接定位；阅读一个用例不需要跨越无意义的包装层。
- 不引入无证据的目录模板、工具、设计模式或框架习惯。
- 导入导出、路由、测试、样式和公开契约随重命名或删除同步更新。
- 变更通过与风险相称的适用验证，或明确列出未运行项、风险与准确原因；最终 Diff 不包含与任务无关的格式化噪音。
