# My Codex Skills

个人维护的 Codex Skills 集合，用于把常用工作流沉淀为可复用的指令。

## 已包含的 Skills

| Skill | 用途 |
| --- | --- |
| `standardize-web-code` | 统一 Web、Node.js 与全栈项目的命名、模块组织、类型、安全、无障碍和验证方式，覆盖 Vue、Nuxt、React、Next.js、Express 等常见技术栈。 |
| `worklog` | 从 Git 提交、最近修改文件、编辑器记录和 Shell 历史中汇总工作内容，生成日报或周报。 |
| `git-commit` | 仅基于 Git 暂存区内容生成符合项目历史规范的提交信息并执行提交，避免误提交未暂存改动。 |

## 使用

将本仓库的 `skills` 目录放在 Codex 的 skills 目录下，Codex 会按每个 Skill 的 `SKILL.md` 自动识别适用场景。

例如：

- 让 Codex 重构或规范 Web 项目代码时，会使用 `standardize-web-code`。
- 说“写日报”“生成周报”或“总结一下今天做了什么”时，会使用 `worklog`。
- 说“提交代码”“commit 一下”时，会使用 `git-commit`。

## 与 Claude Code 复用

可以通过软链接让 Claude Code 复用同一套 Skills：

```bash
mkdir -p ~/.claude
ln -s ~/.agents/skills ~/.claude/skills
```

如果 `~/.claude/skills` 已存在，请先确认其中没有需要保留的内容，再移除或调整该目录后创建软链接。

## 目录结构

```text
skills/
├── git-commit/
│   └── SKILL.md
├── standardize-web-code/
│   ├── SKILL.md
│   ├── agents/
│   └── references/
└── worklog/
    ├── SKILL.md
    ├── references/
    └── scripts/
```

## 维护约定

- 每个 Skill 以独立目录存放，并以 `SKILL.md` 作为入口。
- 将可复用的详细规则和资料放入 `references/`。
- 将可执行辅助工具放入 `scripts/`，并在 `SKILL.md` 中说明调用方式。
