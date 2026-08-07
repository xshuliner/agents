# My Codex Skills

个人维护的 Codex Skills 集合，用于把常用工作流沉淀为可复用的指令。

## 已包含的 Skills

| Skill | 用途 |
| --- | --- |
| `standardize-web-code` | 统一 Web、Node.js 与全栈项目的命名、模块组织、类型、安全、无障碍和验证方式，覆盖 Vue、Nuxt、React、Next.js、Express 等常见技术栈。 |
| `cocos-creator-v3` | 提供 Cocos Creator 3.8 游戏引擎的全面开发指导，涵盖组件系统、生命周期、事件系统、资源管理、tween 缓动、对象池、UI、物理碰撞及可试玩广告优化。 |
| `git-commit` | 仅基于 Git 暂存区内容生成符合项目历史规范的提交信息并执行提交，避免误提交未暂存改动。不校验分支，main/master 等保护分支也可直接提交。 |
| `skill-creator` | 用于创建新 Skill 或更新既有 Skill 的指导，帮助把领域知识、工作流和工具集成封装为可复用的 Skill 包。 |

## 使用

将本仓库的 `skills` 目录放在 Codex 的 skills 目录下，Codex 会按每个 Skill 的 `SKILL.md` 自动识别适用场景。

例如：

- 让 Codex 重构或规范 Web 项目代码时，会使用 `standardize-web-code`。
- 编写或重构 Cocos Creator 3.x TypeScript 代码、实现游戏功能、优化性能/包体大小时，会使用 `cocos-creator-v3`。
- 说“提交代码”“commit 一下”时，会使用 `git-commit`。
- 说“创建一个 Skill”“把这个流程封装成 Skill”时，会使用 `skill-creator`。

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
├── cocos-creator-v3/
│   ├── SKILL.md
│   └── references/
│       ├── framework/
│       ├── language/
│       └── review/
├── git-commit/
│   └── SKILL.md
├── skill-creator/
│   ├── SKILL.md
│   ├── LICENSE.txt
│   ├── references/
│   └── scripts/
└── standardize-web-code/
    ├── SKILL.md
    ├── agents/
    └── references/
```

## 维护约定

- 每个 Skill 以独立目录存放，并以 `SKILL.md` 作为入口。
- 将可复用的详细规则和资料放入 `references/`。
- 将可执行辅助工具放入 `scripts/`，并在 `SKILL.md` 中说明调用方式。
