# 当日 / 本周 Codex / Claude Code / Pi Agent / TeleAgent / Cursor / Trae / Qoder 会话采集与工作过滤

仅在用户要求从当日或本周活跃的 AI 任务或 session 自动生成报告时读取本文件。

## 先确定工作范围

会话正文可能包含个人信息和无关项目。先确定一个或多个批准的工作根目录，再读取正文。

### 单项目模式（用户指定项目目录）

用户明确指定了项目目录时，工作根目录就是该目录本身。只整理该项目下的工作。

### 汇总模式（用户未指定项目目录）

用户未指定项目目录时，工作根目录按以下优先级确定：

1. 环境变量 `DAILY_REPORT_WORK_ROOTS`。多个目录使用当前操作系统的路径分隔符分开：macOS/Linux 通常为 `:`，Windows 通常为 `;`。
2. 若环境变量未设置，则**不设置目录白名单**，采集所有能发现的会话（汇总模式）。
3. 当前任务明确位于一个工作 Git 仓库时，使用 `git rev-parse --show-toplevel` 得到的源仓库根目录作为补充范围。

将 `~` 展开并解析真实路径。满足以下任一条件的会话进入目录白名单：

1. 实际 `cwd` 位于任一批准工作根目录或其子目录。
2. Codex 会话的实际 `cwd` 位于 Codex worktree 根目录，并且通过 Git common-dir 解析出的源仓库位于任一批准工作根目录或其子目录。

范围安全规则：

- 不要默认扫描用户主目录、磁盘根目录或包含大量无关仓库的宽泛父目录。
- Codex worktree 不能只因实际 `cwd` 位于 `~/.codex/worktrees` 而纳入。使用 `scripts/resolve_codex_session_scope.py` 调用 `git rev-parse --git-common-dir`，以源仓库真实路径决定范围。
- 普通临时目录或其他工作树不享受此例外；不要根据目录名称、remote URL 或会话正文猜测来源。
- Cursor/Trae/Qoder 的工作目录字段位于会话 metadata，不在会话正文里；whitelist 过滤只能利用 metadata，不读正文就丢弃。
- 所有脚本都接受可重复的 `--work-root`；未传参时读取 `DAILY_REPORT_WORK_ROOTS`，两者都没有时会返回错误而不是使用个人默认值。
- **汇总模式**下，如果既未指定项目目录也未设置 `DAILY_REPORT_WORK_ROOTS`，则使用 `--no-filter` 模式采集所有会话。
- TeleAgent daily-log 不携带 `cwd`，目录白名单仅作为元数据写入输出；筛选与相关性判定交给报告作者按用户范围处理。

## 采集流程

1. 按用户当前时区计算目标时间窗。**单日模式**为当日 `00:00:00` 至次日 `00:00:00`；**范围模式**为 `[start-date, end-date + 1天)` 闭开区间，周报默认按周一到周日划分。
2. 同时检查当前环境中可用的所有数据源；某个来源不存在或对应客户端未安装时继续处理其他来源。
3. 先按规范化 `cwd` 执行目录白名单；对 Codex worktree 额外验证 Git common-dir。Cursor/Trae/Qoder 在 metadata 中读取 `cwd`；未通过任一条件的会话不读取正文。
4. 排除当前正在生成报告的任务，避免把"生成报告"写成工作成果。
5. 对白名单内候选读取最近状态与回合摘要。需要确认累计结果或交接关系时再向前翻页；不要加载附件、思考过程、大段命令输出或完整 tool result。
6. 从用户消息、最终答复、状态更新、测试结果、文件变更、提交或推送记录中提取事实。推理摘要和过程性工具输出不能单独作为工作成果。
7. 识别委派来源、同名续接任务、相同工作目录、分支、提交、交付物和连续指标基线，合并为一条成果链。
8. 对跨数据源的同一工作再次去重；不能因为客户端不同而重复累计成果。
9. **范围模式**下，把每个自然日当作独立时间窗分别采，再把多日结果合并输出。同一任务如果跨日连续推进，按交付物合并，只在周报或范围报告中体现"本周新增"或"周期内累计"。

## 数据源总览

| 数据源 | 默认路径 | 关键 metadata 字段 | 唯一 ID |
|---|---|---|---|
| Codex Desktop | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | `session_meta.payload.cwd` | session_meta.id |
| Claude Code | `~/.claude/projects/**/*.jsonl` | 每条记录的 `cwd` + `gitBranch` | sessionId |
| Pi Agent | `~/.pi/agent/sessions/**.jsonl` | 首行 header 的 `cwd` | session.id |
| TeleAgent | `~/.local/share/TeleAgent/memory/daily-log/YYYY-MM-DD.md` | 无 cwd，按 ISO 时间戳过滤 | daily-log 日期 |
| Cursor | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` | `composerHeaders.value.workspaceIdentifier.uri.fsPath` | composerId |
| Trae | `~/Library/Application Support/Trae/User/workspaceStorage/<id>/chatSessions/*.json` | workspace.json → folder URI | session.sessionId |
| Qoder | `~/Library/Application Support/Qoder/User/workspaceStorage/<id>/chatSessions/*.json` | workspace.json → folder URI | session.sessionId |

## Codex 采集

1. 使用当前环境可用的 Codex 任务或线程列表能力读取近期任务；若没有该能力，跳过 Codex 并记录覆盖限制。
3. 对目标时间窗内更新的任务，先按唯一 `cwd` 批量运行范围解析器：

   ```bash
   python3 scripts/resolve_codex_session_scope.py \
     --work-root /path/to/company-projects \
     --cwd /path/from/thread
   ```

   也可使用 `--no-filter` 走汇总模式。

4. 仅对结果中 `included=true` 的任务加载内容。

5. **直接读取** 走 `collect_codex_sessions.py`：

   ```bash
   # 日报
   python3 scripts/collect_codex_sessions.py \
     --date YYYY-MM-DD \
     --work-root /path/to/company-projects

   # 周报 / 范围
   python3 scripts/collect_codex_sessions.py \
     --start-date YYYY-MM-DD --end-date YYYY-MM-DD \
     --work-root /path/to/company-projects
   ```

   脚本读取 `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`，只消费 `response_item.payload.type=message` 且 role ∈ {user, assistant} 的记录；忽略 developer/system、tool call 与 tool result。

## Claude Code 采集

从技能目录运行自带脚本：

```bash
# 日报
python3 scripts/collect_claude_sessions.py \
  --date YYYY-MM-DD --work-root /path/to/company-projects

# 周报 / 范围
python3 scripts/collect_claude_sessions.py \
  --start-date YYYY-MM-DD --end-date YYYY-MM-DD \
  --work-root /path/to/company-projects
```

- 脚本读取 `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/**/*.jsonl`，忽略 `subagents/`，依据每条记录的时间戳判断是否在时间窗内，并依据记录中的真实 `cwd` 执行白名单。
- 只消费脚本输出中的用户或助手文本摘要、标题、目录、分支和时间；脚本不读取 tool-results、附件、思考块或子代理 transcript。

## Pi Agent 采集

```bash
python3 scripts/collect_pi_sessions.py \
  --date YYYY-MM-DD --work-root /path/to/company-projects
```

- 脚本默认读取 `${PI_CODING_AGENT_SESSION_DIR:-${PI_CODING_AGENT_DIR:-~/.pi/agent}/sessions}` 中的顶层 session JSONL；兼容 `--pi-home` 和 `--session-dir` 显式覆盖。
- Pi Agent session 是追加式消息树。只消费当前 leaf 的有效分支；v1 线性 session 按文件顺序读取。

## TeleAgent 采集

```bash
# 日报
python3 scripts/collect_teleagent_sessions.py --date YYYY-MM-DD

# 周报 / 范围
python3 scripts/collect_teleagent_sessions.py \
  --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

- 脚本读取 TeleAgent 每日工作日志，**默认路径** `${TELEAGENT_HOME:-~/.local/share/TeleAgent}/memory/daily-log/YYYY-MM-DD.md`；可用 `--teleagent-home` 或 `--daily-log-dir` 覆盖；环境变量 `TELEAGENT_HOME` / `TELEAGENT_DIR` / `TELEAGENT_DAILY_LOG_DIR` 也可生效。
- 每条日志的格式为 `- [ISO8601 时间戳] 描述文本`，脚本按目标时间窗过滤每行的时间戳。
- TeleAgent 日志不携带 `cwd`、分支、sessionId，所以无法做项目级白名单过滤；目录白名单仅作为元数据写入输出。

## Cursor 采集

```bash
python3 scripts/collect_cursor_sessions.py \
  --date YYYY-MM-DD --work-root /path/to/company-projects
```

Cursor 把全局聊天索引与消息气泡存在 WAL-mode SQLite：

- 路径：`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`（环境变量 `CURSOR_HOME` 可覆盖）
- 表 `composerHeaders`：每条聊天一行，含 `composerId`、`createdAt`、`lastUpdatedAt`、`isSubagent`、`value(JSON)`
- `value.workspaceIdentifier.uri.fsPath` 给出该聊天对应的真实项目路径 → 作为 cwd 白名单依据
- `value.name` 是用户命名；draft 仅 `subtitle`（首条消息片段）
- 表 `cursorDiskKV`：
  - `composerData:<composerId>` → JSON，含 `fullConversationHeadersOnly` 数组（每条 `{bubbleId, type, createdAt}`），给出**逐消息时间戳**
  - `bubbleId:<composerId>:<bubbleId>` → JSON，含 `text`（`type=1` 用户、`type=2` 助手）

采集流程：

1. 把 `state.vscdb` + `-wal` + `-shm` 复制到临时目录，再以 `mode=ro` 打开（Cursor 运行时数据库是锁住的）。
2. 过滤 `composerHeaders` 中 `isSubagent=0` 且 `isArchived=0` 且 `lastUpdatedAt || createdAt` 落在时间窗内的行。
3. 过滤后对每条 composer 读 `composerData` 的 `fullConversationHeadersOnly`，按 `createdAt` 精确过滤到时间窗，再去 `cursorDiskKV` 取 bubble 文本。
4. 对助手消息剥离 `<think>…</think>` 思考块。

## Trae 与 Qoder 采集（VSCode 派生编辑器）

```bash
python3 scripts/collect_trae_sessions.py \
  --date YYYY-MM-DD --work-root /path/to/company-projects

python3 scripts/collect_qoder_sessions.py \
  --date YYYY-MM-DD --work-root /path/to/company-projects
```

两者都基于 `vscode_fork_common.py` 共享解析逻辑：

- Trae 默认数据目录：`~/Library/Application Support/Trae`（`TRAE_HOME` 可覆盖；脚本同时探测 `Trae CN`、`Trae-CN` 等变体）
- Qoder 默认数据目录：`~/Library/Application Support/Qoder`（`QODER_HOME` 可覆盖）
- 会话文件：`<app>/User/workspaceStorage/<workspace-id>/chatSessions/<sessionId>.json`
  - `workspace.json` 给 `folder` URI（`file://…`），反解得到 cwd 用于白名单
  - 每条 session 的 `requests[]` 含 `timestamp(ms)` + `message.text` + `response[*].value`，分别对应 user/assistant
- 兜底：部分版本把 bubble 存到 `<app>/User/globalStorage/state.vscdb::cursorDiskKV` 的 `bubbleId:<id>:<bid>` —— 复用 `collect_global_state_bubbles` 备用读取

## 工作相关性判定

目录白名单决定"可以读取"，岗位和汇报目标决定"应该写入"。判断标准不是是否花了时间，而是内容是否服务于用户需要向组织、客户、团队或项目负责人汇报的目标和交付。

优先级从高到低：

1. 用户本次明确指定的岗位、项目、目录和纳入或排除范围。
2. 会话是否在批准目录内产生与岗位目标直接相关的代码、内容、设计、测试、数据、运营结果、业务结论、协作结果或其他交付物。
3. 下方默认排除类别，用于处理白名单内仍与本次汇报无关的元会话。

不要使用职业刻板规则。例如内容、设计、营销或 AI 工具建设可能正是用户的岗位交付；只要用户范围和证据支持，就应纳入。

## 默认纳入

- 需求分析、方案设计、代码或内容生产、测试、缺陷处理、发布、运营和运行保障等岗位交付。
- 形成明确结论或交付物的调研、评审、架构评估、安全审计、数据分析和用户研究。
- 与目标进度直接相关的计划、风险、决策、跨团队协作和待办。
- 为组织或项目交付而建设的测试、CI/CD、质量门禁、自动化、知识库或工程平台能力。

## 默认排除

除非用户明确说明属于岗位职责或本次汇报范围，否则不进入报告：

- 当前报告生成、聊天整理、任务归档或重命名等元操作。
- 与批准项目无关的生活、娱乐、个人事务和个人内容。
- 没有形成项目决策或交付物的随手问答、内容消费和工具探索。
- 仅改善个人 AI 使用体验的全局配置或试验；若 AI 工具、skill 或自动化本身就是岗位交付，则应纳入。
- 已放弃分支、被后续结论推翻的中间结果和仅有过程、没有可验证进展的噪声。

## 混合任务、去重与结果状态

- 同一会话包含工作交付和个人操作时，只记录工作范围内的交付及其验证结果。
- 同一会话先调研通用工具、后形成项目实施计划时，只记录被项目采用的结论、计划和交付物。
- 优先使用最新、证据最完整的回合描述累计成果；早期中间值只用于计算可信增量。
- 不要把上游主任务和下游委派任务的同一批测试、同一提交或同一文档分别计数。
- 不同客户端若出现相同提交哈希、文件集合、测试批次或首尾一致的指标链，视为同一成果；合并上下文但指标只计一次。
- 仍在运行的任务写为"进行中"，只列已经验证的阶段结果；不要推测最终状态。
- 周报要明确"本周累计 vs 历史累计"。仅当周期内新增的事实才能算入"本周"；跨日连续推进的任务合并成一条成果链，必要时标注首次发生日期。
- 跨日任务可以纳入目标日期实际发生的新进展，但不要把历史累计更新冒充为当日新增。无法拆分增量时写"截至当日累计"，并明确口径。

## 隐私与输出

- 不在报告中复制 API key、token、密码、Cookie、私密对话、会话文件路径或完整命令输出。
- 默认只输出报告正文，不列出被排除会话或本地目录。
- 用户要求审计时，使用简短表格列出任务名称、判定（纳入/排除/混合）和一句原因，不泄露会话正文。
- 自动采集且来源不完整时，在正文末尾简要说明实际检查了哪些客户端；对不可用或没有记录的来源使用中性事实，不暗示已完整扫描。

## 扩展新数据源

所有采集脚本都基于 `scripts/collector_common.py`：

```python
from collector_common import (
    add_common_args, resolve_range, local_bounds,
    resolve_roots_or_empty, parse_timestamp, redact,
    extract_text_blocks, is_under,
    make_message, make_session, truncate_messages,
    emit_output, emit_error,
)
```

新增数据源的标准步骤：

1. 复制最小的现有 collector（如 `collect_teleagent_sessions.py`）作为模板。
2. 用 `add_common_args` 统一 `--date` / `--start-date` / `--end-date` / `--work-root` / `--no-filter` / `--max-messages` / `--max-text-chars`。
3. 实现该数据源独有的"发现 + metadata 校验 + 逐条消息提取"逻辑；只提取 `user`/`assistant` 角色的可见文本。
4. 用 `make_message / make_session / truncate_messages / emit_output` 写出与其它源完全一致的 JSON envelope。
5. 在本文件"数据源总览"和 SKILL.md 的描述中追加新源。
6. 至少用一份真实样本（含 cwd、时间戳、user/assistant 文本）跑通 `--date` + `--no-filter` 验证；再用一份 whitelist 验证白名单生效。