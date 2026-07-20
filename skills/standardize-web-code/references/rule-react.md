# React 规则

- 使用 PascalCase 组件与 `useX` Hook。组件内按外部 Hook/配置、状态与 Ref、派生值、effect、操作和渲染组织；保持仓库既有顺序。
- 不保存可派生状态；`useMemo`/`useCallback` 只用于真实计算成本、引用稳定或下游契约，不作默认优化。effect 只同步外部系统，依赖完整且清理订阅/请求。
- Props 是首选的局部数据流；Context 只放稳定的跨树依赖，不替代一切局部状态。组件抽取遵循通用抽象门槛。
- 不把 Next.js 的 Server/Client 规则套入普通 React；根据项目入口与构建工具处理数据加载、路由和环境变量。
