# 手动并行采集（collect.sh 不可用时的兜底）

**只在 `scripts/collect.sh` 缺失或整体失败时使用**。能跑脚本就一定先跑脚本——脚本已经处理了 BSD/GNU 兼容、JSON 解析、sqlite3 依赖等坑。

如果退化到手动模式，**4 个 Bash 调用必须并行发起**（互不依赖），不要串行。

## 1. Git 提交记录

```bash
# daily: SINCE="$(date +%Y-%m-%d) 00:00"
# weekly: SINCE="$(python3 -c "import datetime; d=datetime.date.today()-datetime.timedelta(days=datetime.date.today().weekday()); print(d.strftime('%Y-%m-%d'))") 00:00"
USER_NAME="$(git config --global user.name 2>/dev/null)"

# 扫描用户目录下的 git 仓库
for proj in $(find $HOME/Documents $HOME/Desktop $HOME/workspace $HOME/projects $HOME/repos -maxdepth 5 -name .git -type d 2>/dev/null | sed 's|/.git$||'); do
  cd "$proj" && git log --since="$SINCE" --author="$USER_NAME" --pretty=format:"%h|%ai|%s" 2>/dev/null
done
```

## 2. 最近修改文件

```bash
# daily: -mtime -1（24h 内）
# weekly: -mtime -7（7 天内）
find $HOME -maxdepth 6 -type f \( -mtime -1 \) \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/Library/*" \
  -not -path "*/.cache/*" \
  -not -path "*/.npm/*" \
  -not -path "*/.next/*" \
  -not -path "*/dist/*" \
  -not -path "*/.nuxt/*" \
  -not -path "*/.output/*" \
  -not -path "*/.venv/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*/.omc/*" \
  -not -path "*/.claude/*" \
  -not -path "*/.cursor/*" \
  -not -path "*/.vscode/*" 2>/dev/null | head -50
```

## 3. 编辑器最近打开

```bash
# VSCode
VSCODE_DB="$HOME/Library/Application Support/Code/User/globalStorage/state.vscdb"
[ -f "$VSCODE_DB" ] && sqlite3 "$VSCODE_DB" \
  "SELECT v FROM ItemTable WHERE k='history.recentlyOpenedPathsList' LIMIT 1;" 2>/dev/null | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print('\n'.join(x.get('fileUri',{}).get('path','') for x in d.get('entries',[])[:30]))"

# Cursor
CURSOR_DB="$HOME/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
[ -f "$CURSOR_DB" ] && sqlite3 "$CURSOR_DB" \
  "SELECT v FROM ItemTable WHERE k='history.recentlyOpenedPathsList' LIMIT 1;" 2>/dev/null | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print('\n'.join(x.get('fileUri',{}).get('path','') for x in d.get('entries',[])[:30]))"
```

## 4. Shell history

```bash
# 优先用交互式 history
history -i 2>/dev/null | head -500

# 兜底读文件
HIST="$HOME/.zsh_history"
[ ! -f "$HIST" ] && HIST="$HOME/.bash_history"

# 检查是否是 EXTENDED_HISTORY 格式（首行含 ": <epoch>:<duration>;"）
head -1 "$HIST" 2>/dev/null | grep -q '^: [0-9]\+:[0-9]\+;' && echo "EXTENDED" || echo "BASIC"
```

**关键判断**：
1. EXTENDED 格式 → 可以按时间戳精确过滤今日/本周的命令
2. BASIC 格式 → 只能取全部最近 N 条；必须在最终输出里告诉用户"history 没有时间戳，本次无法精确按日过滤"

## 5. 退出条件

4 个源全部失败时（即全新电脑、没装 git、没装 sqlite3、history 为空），停止采集并触发异常处理第一条（用 AskUserQuestion 让用户口述）。**不要伪造数据**。
