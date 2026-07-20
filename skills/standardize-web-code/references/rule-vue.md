# Vue 规则

- 使用项目既有的 Composition API 或 Options API；新代码不为统一而重写另一种风格。SFC 与组件使用 PascalCase，模板事件沿用仓库的 kebab-case 或 camelCase。
- Props 是只读输入；以 emit 或受控 `v-model` 表达向上通信。声明 props、emits、slots 的业务契约，避免暴露父组件内部细节。
- 用 `computed` 表示派生值；`watch`/`watchEffect` 只同步外部副作用，不复制可推导状态。复杂模板转换放入具名 computed 或领域函数。
- Composable 以 `useX` 命名，仅承载可复用响应式生命周期；普通函数不使用 `use` 前缀。`ref`/`reactive` 不加无意义 `Ref` 后缀，模板 DOM/组件引用可加。
- 注意响应式解构、生命周期清理、异步竞争和 Suspense/Teleport/transition 边界；删除 Scoped CSS 前验证深度选择器和过渡类。
