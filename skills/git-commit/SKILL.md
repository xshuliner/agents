---
name: git-commit
description: 当用户表达「提交代码」「commit 一下」「提交本次修改」「提交并 push」「提交并打 tag」等把修改入库的意图时，必须启用本 skill。仅检查并提交 Git 暂存区中的变更，严格依据 staged diff 生成符合项目历史规范、包含 type、scope 与 emoji 的 commit message；不得读取、描述、暂存或提交未暂存变更。
---

# Git Commit

只把暂存区视为本次提交的事实来源和授权边界。生成 message、执行 commit、验证结果；不要修改代码。

## 不可违背的边界

1. 只提交 `git diff --cached` 展示的内容。
2. 只依据 staged diff 判断改动意图、`type`、`scope`、主题和 body。
3. 不读取 `git diff`（未暂存 diff），不根据未暂存文件名或内容推断、补充或修正提交描述。
4. 不运行 `git add`，不自动暂存任何文件或 hunks。未进入暂存区即视为用户不准备提交。
5. 不在 commit message 或最终改动摘要中描述未暂存内容。必要时只能说明“仍有未暂存变更，未纳入本次提交”。
6. 暂存区为空时不创建 commit；直接说明“暂存区没有可提交的变更”。除非用户明确要求，否则不创建空提交。
7. 不修改、格式化、删除或恢复工作区文件；本 skill 只执行提交相关的只读检查与 `git commit`。
8. 不使用 `--no-verify`、`--no-gpg-sign`，也不绕过失败的 hook 或签名。

`git status --short` 只用于识别 staged/unstaged 状态和提交后复核，不得把其中的未暂存部分作为提交描述依据。

## 工作流

### 1. 确认仓库和分支

运行：

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short
```

如果不在 Git 仓库中，停止并说明。

若当前分支为 `main`、`master`、`develop`、`release/*`、`hotfix/*` 等通常受保护的分支，先让用户选择切换新分支、仍在当前分支提交或取消。不要擅自切换或创建分支。

### 2. 读取暂存区

运行：

```bash
git diff --cached --quiet
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

- `git diff --cached --quiet` 返回 0：暂存区为空，停止。
- 返回 1：继续检查 staged diff。
- 其他返回码：视为 Git 错误，停止并说明。

必须完整理解 staged diff，不能只看文件名或统计信息猜测。对于二进制文件，可结合 staged 文件名、属性和可获得的暂存区元数据作最小必要判断，但不得转而读取未暂存版本补充描述。

### 3. 检查提交规范和历史

按需运行：

```bash
git log --format=%s -n 20
git config --get commit.gpgsign
git config --get user.signingkey
git config --get user.name
git config --get user.email
```

检查仓库内已有的 commitlint、Commitizen、贡献指南或代理指令。规则优先级：

1. 用户本次明确要求
2. 仓库内 commit 规则
3. 项目历史风格
4. 本 skill 默认规范

历史记录只用于确定语言和格式风格，不能用来补充 staged diff 中不存在的改动。

默认使用中文；若最近 20 条非合并提交中 80% 以上的主题为非中文，则跟随项目历史语言。没有历史记录时使用中文。

### 4. 检查暂存内容是否可提交

仅针对 staged diff 检查：

- 是否混入 `.env`、私钥、token、证书、API key、密码或其他疑似敏感信息。
- 是否包含日志、调试文件、构建产物或明显无关内容。
- 是否混合多个彼此独立的主题。

发现敏感信息时停止，让用户选择先自行移出暂存区、确认继续或取消。

发现多个独立主题时，不要自行重排暂存区，也不要连续创建多个 commit。列出基于 staged diff 的分组建议，让用户自行调整暂存区后再继续，或明确授权当前 staged 内容作为一个 commit 提交。

### 5. 生成 commit message

格式：

```text
<emoji> <type>(<scope>): <祈使句主题>

[可选 body，每项以 "- " 开头]

[可选 footer]
```

必须满足：

- 包含 emoji、type 和明确的 scope。
- 主题具体描述 staged diff 做了什么，不使用过去时。
- 主题不以句号结尾，长度不超过 72 字符。
- body 只描述 staged diff 中能直接确认的内容，每行不超过 72 字符。
- issue 或需求编号只在 staged 内容、用户输入或可靠仓库上下文明确提供时引用；不得编造。
- staged diff 无法支持的动机、效果、修复结果或实现细节不得写入 message。

禁止使用空泛表述：`update`、`fix bug`、`wip`、`misc`、`修改代码`、`优化一下`、`提交本次修改`。

### Type 与 Emoji

| type | emoji | 使用条件 |
|---|---|---|
| feat | ✨ | 新增用户原本没有的能力 |
| fix | 🐛 | 修复明确的错误行为 |
| improve | 🚀 | 增强已有功能或体验 |
| refactor | 🔄 | 调整结构且不改变外部行为 |
| perf | ⚡ | 纯性能优化 |
| style | 💅 | 仅格式或视觉样式变化 |
| docs | 📚 | 文档或注释 |
| test | 🧪 | 测试用例或测试配置 |
| config | ⚙️ | 工具、构建或环境配置 |
| ci | 🤖 | CI/CD 流程 |
| chore | 🔧 | 依赖、清理等维护工作 |
| revert | ⏪ | 回滚已有提交 |

边界判定：

- 新能力用 `feat`；已有能力增强用 `improve`。
- 只有性能维度变化用 `perf`；包含功能或体验变化用 `improve`。
- 外部行为不变用 `refactor`；用户可感知变化用 `improve`。
- 纯格式用 `style`；命名或结构调整用 `refactor`。

### Scope

依次选择：

1. staged 变更所属模块或功能域。
2. staged 变更所在目录、页面、组件或配置对象。
3. 项目历史中与该模块对应的既有 scope。

避免使用 `core`、`project` 等宽泛 scope，除非 staged 变更确实覆盖整个领域。不要借助未暂存变更选择 scope。

### Body

当 staged 变更跨多个文件、包含值得说明的技术细节或仅靠主题无法准确概括时添加 body。单一小改动且主题已完整时省略 body。

示例：

```text
✨ feat(auth): 支持登录态自动刷新

- 增加令牌过期检测与刷新流程
- 清理刷新失败后的登录状态
```

```text
⚙️ config(lint): 统一代码格式检查规则
```

### 6. 执行提交

无 body：

```bash
git commit -m "⚙️ config(lint): 统一代码格式检查规则"
```

有 body：

```bash
git commit -m "✨ feat(auth): 支持登录态自动刷新" \
  -m "- 增加令牌过期检测与刷新流程
- 清理刷新失败后的登录状态"
```

不要用 shell 拼接未经检查的动态内容。执行前确保命令中的 message 与已审核内容完全一致。

用户明确要求 amend 时：

1. 确认暂存区只包含要补入上一个 commit 的内容。
2. 运行 `git commit --amend`，不得加入绕过参数。
3. 用 `git log -1 --format=fuller` 复核结果。

未明确要求时不得主动 amend。

### 7. 处理失败

- hook 失败：读取输出并说明原因。由于本 skill 不修改代码，不要自动运行会改写文件的 lint/format 修复命令；让用户修复并重新暂存后再试。
- GPG 失败：说明密钥、pinentry 或配置问题；不得绕过签名。
- Git identity 缺失：停止并提示用户配置 `user.name` 和 `user.email`。
- 权限或锁文件错误：先做非破坏性诊断；无法安全解决时停止并说明。

### 8. 提交后复核

运行：

```bash
git log -1 --format='%H%n%s%n%b'
git status --short
```

确认最新 commit message 正确，原 staged 内容已提交，没有意外新增的 staged 变更。

若仍有未暂存变更，只报告其存在且未纳入本次提交；不要列文件、概括内容或解释这些改动。若仍有 staged 变更，明确报告暂存区仍有残留，因为这可能意味着提交不完整或 hook 改写了状态。

## 最终回复

提交成功时：

```text
已完成提交：

<commit hash> <commit subject>

<可选：仅依据已提交 staged diff 的一句话摘要>
当前暂存区已清空。
```

存在未暂存变更时，只追加：

```text
工作区仍有未暂存变更，未纳入本次提交。
```

不得描述未暂存变更是什么。

## Push 和 Tag

只有用户明确要求时才执行 push 或创建 tag。commit 成功后再执行，并沿用仓库现有远端、分支和 tag 规范；push、强推、创建或覆盖 tag 属于独立操作，不因用户只说“提交”而自动执行。
