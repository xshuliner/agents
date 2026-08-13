# 前端样式与 Tailwind

- 先检查 `tailwind.config.*`、PostCSS/Vite 配置、依赖和相邻组件；项目已采用 Tailwind 时，常规布局、间距、排版、颜色、响应式和状态样式优先使用现有 Tailwind utility class，而非新增单用途 CSS。不要为此在未采用 Tailwind 的项目中引入依赖或重写既有样式体系。
- 使用仓库既有的 class 排序、合并、条件拼接和设计 token 约定；条件 class 必须由可静态扫描的完整字符串组成，避免运行时拼接任意 utility，确保构建器能生成所需样式。
- 将重复出现且语义稳定的组合沉淀为既有组件、设计 token 或公共样式；不要为了少写几个 class 创建只使用一次的组件，也不要在每个组件复制一长串相同 class。
- 仅在 utility 无法清晰表达、需要伪元素/复杂选择器/关键帧、第三方 DOM 覆盖或确有跨处复用时写 CSS；样式归属到对应功能，选择器保持局部、语义化且避免全局泄漏。优先评估现有 Tailwind variant、`before:`/`after:` 等能力，仍不清晰时再手写。
- 不把动态外部输入直接拼进 class 或样式值；改用受控映射或校验后的 CSS 变量。修改样式后核验响应式、hover/focus/disabled、深色模式（如项目启用）、溢出和键盘焦点状态。
- 先复用项目已有的交互状态、动效 token、组件和主题风格；只有缺失时才增加局部实现。可点击控件使用语义化 `button`/`a`，或补全等价键盘语义；交互可用时提供可感知的 `hover`、`active` 和键盘 `focus-visible` 反馈。若现有设计未规定，优先以轻微透明度变化实现 hover/active，并为非禁用的可点击区域使用 `cursor: pointer`。
- 对展开/收起、弹窗、页面跳转和组件切换，优先采用项目已有的短促、克制过渡；仅在状态变化确实可感知时添加，避免装饰性或阻塞操作的动画。遵从现有 reduced-motion 方案；缺失时用 `prefers-reduced-motion` 降低或关闭非必要动画。
