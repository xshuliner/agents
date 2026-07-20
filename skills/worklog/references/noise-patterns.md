# 噪音文件清单（聚类阶段剔除）

聚类"最近修改文件"时，遇到以下路径/文件一律剔除，不归入"今日/本周工作"。

## 1. 构建产物

1. `.nuxt/`、`.output/`、`.data/`、`.nitro/`
2. `.cache/`、`.next/`、`dist/`、`build/`
3. `node_modules/`、`.venv/`、`__pycache__/`
4. `.tsbuildinfo`

## 2. 工具与 agent 状态

1. `.omc/`、`.omx/`、`.claude/`、`.codex/`
2. `.cursor/`、`.vscode/`、`.idea/`、`.agents/`
3. `.fleet/`、`.obsidian/`

## 3. 日志与锁文件

1. `*.log`、`.husky/_/*`（部分）
2. `pnpm-lock.yaml`、`package-lock.json`、`yarn.lock`
3. 任何 `*.lock`

## 4. 本地配置

1. `.env`、`.env.*`（环境变量文件，含密钥风险）
2. `settings.local.json`（本地覆盖配置）
3. `.DS_Store`（macOS 系统文件）
4. `.prettierignore`（部分场景下是噪音）

## 5. 兜底：交叉对比 .gitignore

1. 对每个项目跑一遍 `git status` / `cat .gitignore`
2. 被 .gitignore 排除的文件即使在 find 结果里也要剔除
3. 这一步能发现项目特定的噪音模式（比硬编码更准）
