# 通用命名规则

- 先定义领域名词；组件、路由、状态、类型、接口和测试对同一概念复用同一核心词。
- 用团队成员一眼能懂的常用词直接说明实体、范围和动作，如 `selectedOrder`、`paymentStatus`、`retryCount`；不要把业务变量、文件、组件、函数或类型命名为 `data`、`info`、`item`、`value`、`result`、`temp`、`m`、`n` 等脱离上下文的泛名。仅限极短、无需业务解释的局部数学公式或坐标时，才可使用行业通用的单字母符号。
- 不为显得专业而使用生僻英语；优先使用简单、可搜索且含义准确的词。确有团队共识的生僻中文专业术语时，可使用其中文拼音首字母作为领域缩写；首次定义要能从相邻类型、模块或团队术语表辨识其含义，并在整个领域内保持同一缩写，禁止临时造缩写或同词多缩写。
- 文件名服从框架和仓库；同一目录不混用命名风格。组件通常为 PascalCase，测试与被测模块对应。
- 同一领域的同级文件与目录使用相同、稳定的领域前缀，使资源管理器按族群聚合，例如 `payment-form/`、`payment-form.schema.ts`、`payment-form.test.ts`；先遵守框架保留文件名和仓库既有后缀约定，不为前缀破坏路由或自动扫描。
- 让前缀表达业务归属，后缀表达角色；避免 `utils.ts`、`types.ts`、`index.ts` 一类脱离领域的泛名。仅在仓库已把 barrel 导出作为明确约定时使用 `index.ts`。
- 函数以行为命名：`get`（同步读取）、`list`、`build`、`create`、`normalize`、`parse`、`format`、`validate`、`handle`（事件边界）和 `fetch`/`save`（异步业务动作）。避免 `do`、`process`、`manage` 等弱语义词，除非是领域术语。
- 布尔值使用 `is`、`has`、`can`、`should` 等正向前缀；集合用复数；索引用 `ByX`；数量用 `Count`；度量携带单位，如 `elapsedMs`。
- 状态与更新操作共享名词，如 `publishPhase` / `setPublishPhase`；派生值命名为事实，不叫 `data` 或 `result`。
- 类型按角色后缀：`XProps`、`XParams`、`XInput`、`XResult`、`XConfig`。只在项目明确分层时使用 DTO/Entity/Model/Schema。
- 公开导出、API 字段、持久化键和环境变量是契约；重命名后搜索旧名及字符串、模板、路由、依赖注入与测试引用。
