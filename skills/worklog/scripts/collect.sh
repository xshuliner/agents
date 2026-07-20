#!/bin/bash
# worklog collect.sh
# 采集今日/本周的工作痕迹，输出结构化文本供 skill 汇总使用
# 用法: bash collect.sh <daily|weekly> [path1] [path2] ...
#
# 参数支持:
#   模式: daily / weekly / 日报 / 周报 （中英文都会被映射）
#   路径: 可选 1+ 个项目绝对路径。传了则只看这些路径下的工作内容
set -u

# 第一个参数是模式
RAW_MODE="${1:-daily}"
case "$RAW_MODE" in
  daily|日报|d) MODE="daily" ;;
  weekly|周报|w) MODE="weekly" ;;
  *)
    echo "❌ 用法: bash collect.sh <daily|weekly|日报|周报> [path1] [path2] ..." >&2
    exit 2
    ;;
esac
shift

# 剩余参数是可选的项目路径
USER_PATHS=("$@")
USE_USER_PATHS="false"
if [ ${#USER_PATHS[@]} -gt 0 ]; then
  USE_USER_PATHS="true"
  # 校验 + 规范化
  RESOLVED=()
  for p in "${USER_PATHS[@]}"; do
    # 转绝对路径
    if [ -d "$p" ]; then
      ABS="$(cd "$p" && pwd)"
      RESOLVED+=("$ABS")
    elif [ -f "$p" ]; then
      ABS="$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"
      RESOLVED+=("$(dirname "$ABS")")
    else
      echo "⚠️ 路径不存在，已忽略: $p" >&2
    fi
  done
  # 安全赋值（兼容 set -u + 空数组）
  if [ ${#RESOLVED[@]} -gt 0 ]; then
    USER_PATHS=("${RESOLVED[@]}")
  else
    USER_PATHS=()
  fi
  if [ ${#USER_PATHS[@]} -eq 0 ]; then
    echo "❌ 所有指定路径都无效，终止" >&2
    exit 2
  fi
fi

# ---------- 0. 时间窗口 ----------
case "$MODE" in
  daily)
    SINCE_DATE="$(date +%Y-%m-%d)"
    MTIME="-1"
    LABEL="今日"
    ;;
  weekly)
    SINCE_DATE="$(python3 -c "import datetime; d=datetime.date.today()-datetime.timedelta(days=datetime.date.today().weekday()); print(d.strftime('%Y-%m-%d'))" 2>/dev/null || date -v -7d +%Y-%m-%d)"
    MTIME="-7"
    LABEL="本周"
    ;;
esac

USER_NAME="$(git config --global user.name 2>/dev/null || echo "$USER")"
HAVE_GIT="false"
HAVE_HIST="false"
HAVE_EDITOR="false"
HAVE_FIND="false"
EXTENDED_HISTORY="false"

# ---------- 1. Git 提交记录 ----------
echo "=== GIT (since $SINCE_DATE, author=$USER_NAME) ==="

if [ "$USE_USER_PATHS" = "true" ]; then
  # 用户指定了路径：只查这些路径下的 .git
  ALL_PROJECTS=""
  for p in "${USER_PATHS[@]}"; do
    [ -d "$p/.git" ] && ALL_PROJECTS="$ALL_PROJECTS
$p"
  done
  ALL_PROJECTS=$(echo "$ALL_PROJECTS" | grep -v '^$' | sort -u)
  echo "  📌 仅扫描用户指定路径（共 $(echo "$ALL_PROJECTS" | wc -l | tr -d ' ') 个）："
  for p in "${USER_PATHS[@]}"; do
    RELATIVE="${p#$HOME/}"
    echo "    - $RELATIVE"
  done
else
  CANDIDATES=(
    "$HOME/Documents/01_ProjectXshuliner"
    "$HOME/Documents/02_ProjectWRKJ"
    "$HOME/Documents/03_Personal"
    "$HOME/Documents/04_Work"
    "$HOME/Desktop"
    "$HOME/workspace"
    "$HOME/projects"
    "$HOME/repos"
  )
  AUTO_PROJECTS=$(find "$HOME/Documents" "$HOME/Desktop" "$HOME/workspace" "$HOME/projects" "$HOME/repos" -maxdepth 5 -name ".git" -type d 2>/dev/null | sed 's|/.git$||' | sort -u)
  ALL_PROJECTS=$(printf "%s\n%s\n" "$(printf "%s\n" "${CANDIDATES[@]}")" "$AUTO_PROJECTS" | sort -u | grep -v '^$')
fi

GIT_TOTAL=0
if command -v git >/dev/null 2>&1; then
  HAVE_GIT="true"
  for proj in $ALL_PROJECTS; do
    [ -d "$proj/.git" ] || continue
    RELATIVE="${proj#$HOME/}"
    OUT=$(cd "$proj" && git log --since="$SINCE_DATE 00:00" --author="$USER_NAME" --pretty=format:"%h|%ai|%s" 2>/dev/null)
    if [ -n "$OUT" ]; then
      COUNT=$(echo "$OUT" | wc -l | tr -d ' ')
      echo "  📁 $RELATIVE ($COUNT 条)"
      echo "$OUT" | while IFS='|' read -r hash date msg; do
        echo "    [$hash] $date  $msg"
      done
      GIT_TOTAL=$((GIT_TOTAL + COUNT))
    fi
  done
fi
[ "$GIT_TOTAL" -eq 0 ] && echo "  (无 $LABEL 提交)"

# ---------- 2. 最近修改文件 ----------
echo ""
echo "=== FILES (find -mtime $MTIME) ==="
if command -v find >/dev/null 2>&1; then
  HAVE_FIND="true"
  SEARCH_ROOTS=()
  if [ "$USE_USER_PATHS" = "true" ]; then
    SEARCH_ROOTS=("${USER_PATHS[@]}")
  else
    for d in "$HOME/Documents" "$HOME/Desktop" "$HOME/workspace" "$HOME/projects" "$HOME/repos" "$HOME/Work"; do
      [ -d "$d" ] && SEARCH_ROOTS+=("$d")
    done
    [ ${#SEARCH_ROOTS[@]} -eq 0 ] && SEARCH_ROOTS=("$HOME/Documents")
  fi

  FILES=$(find "${SEARCH_ROOTS[@]}" -maxdepth 8 -type f -mtime "$MTIME" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/.nuxt/*" \
    -not -path "*/.output/*" \
    -not -path "*/.data/*" \
    -not -path "*/.nitro/*" \
    -not -path "*/.cache/*" \
    -not -path "*/.next/*" \
    -not -path "*/dist/*" \
    -not -path "*/build/*" \
    -not -path "*/.venv/*" \
    -not -path "*/__pycache__/*" \
    -not -path "*/.omc/*" \
    -not -path "*/.omx/*" \
    -not -path "*/.claude/*" \
    -not -path "*/.codex/*" \
    -not -path "*/.agents/*" \
    -not -path "*/.cursor/*" \
    -not -path "*/.vscode/*" \
    -not -path "*/.idea/*" \
    -not -path "*/.fleet/*" \
    -not -path "*/.obsidian/*" \
    -not -path "*/logs/*" \
    -not -path "*/.env" \
    -not -path "*/.env.*" \
    -not -name "*.log" \
    -not -name "*.lock" \
    -not -name "pnpm-lock.yaml" \
    -not -name "package-lock.json" \
    -not -name "yarn.lock" \
    -not -name "settings.local.json" \
    -not -name ".DS_Store" 2>/dev/null | head -80)

  if [ -n "$FILES" ]; then
    FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')
    echo "  共 $FILE_COUNT 个文件（前 80 个）："
    echo "$FILES" | sed 's|^|    |'
  else
    echo "  (无最近修改文件)"
  fi
fi

# ---------- 3. 编辑器最近打开 ----------
echo ""
echo "=== EDITOR (VSCode / Cursor state.vscdb) ==="
for DB_PATH in \
  "$HOME/Library/Application Support/Code/User/globalStorage/state.vscdb" \
  "$HOME/Library/Application Support/Cursor/User/globalStorage/state.vscdb"; do
  [ -f "$DB_PATH" ] || continue
  if command -v sqlite3 >/dev/null 2>&1; then
    HAVE_EDITOR="true"
    EDITOR_NAME=$(basename "$(dirname "$(dirname "$(dirname "$DB_PATH")")")")
    echo "  📝 $EDITOR_NAME 最近打开："
    sqlite3 "$DB_PATH" \
      "SELECT v FROM ItemTable WHERE k='history.recentlyOpenedPathsList' LIMIT 1;" 2>/dev/null | \
    python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    entries = data.get('entries', [])
    for e in entries[:30]:
        uri = e.get('fileUri') or e.get('folderUri') or e.get('workspace') or {}
        path = uri.get('path', '') if isinstance(uri, dict) else str(uri)
        if path and not path.startswith('vscode-'):
            print(f'    {path}')
except Exception:
    pass
" 2>/dev/null
  else
    echo "  ⚠️ 找到 $DB_PATH 但缺少 sqlite3，跳过"
  fi
done
[ "$HAVE_EDITOR" = "false" ] && echo "  (未找到 VSCode/Cursor 数据库，或 sqlite3 未安装)"

# ---------- 4. Shell history ----------
echo ""
echo "=== HISTORY (shell) ==="
HIST_FILE=""
[ -f "$HOME/.zsh_history" ] && HIST_FILE="$HOME/.zsh_history"
[ -z "$HIST_FILE" ] && [ -f "$HOME/.bash_history" ] && HIST_FILE="$HOME/.bash_history"

if [ -z "$HIST_FILE" ]; then
  echo "  (未找到 ~/.zsh_history 或 ~/.bash_history)"
else
  HAVE_HIST="true"
  # 全部用 python 解析（避免 grep 误判中文为 binary，也避免 BSD awk 兼容性）
  python3 -c "
import sys, re, datetime, time
hist_file = '$HIST_FILE'
since_date = '$SINCE_DATE'
since_epoch = int(time.mktime(datetime.datetime.strptime(since_date, '%Y-%m-%d').timetuple()))
pattern = re.compile(r'^: (\d+):\d+;(.*)$')
extended = False
hits = 0
total = 0
try:
    with open(hist_file, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            total += 1
            m = pattern.match(line)
            if m:
                extended = True
                epoch, cmd = int(m.group(1)), m.group(2)
                if epoch >= since_epoch:
                    hits += 1
                    print(cmd)
            else:
                # basic 格式：无法判断时间，作为兜底输出（仅显示最近 200 条）
                pass
except Exception as e:
    print(f'  (读取失败: {e})', file=sys.stderr)
    sys.exit(0)

# 输出元信息到 stderr 给主脚本读取
print(f'EXTENDED={extended}', file=sys.stderr)
print(f'TOTAL={total}', file=sys.stderr)
print(f'HITS={hits}', file=sys.stderr)
" > /tmp/worklog_hist_$$.txt 2>/tmp/worklog_hist_meta_$$.txt

  EXTENDED=$(grep '^EXTENDED=' /tmp/worklog_hist_meta_$$.txt 2>/dev/null | cut -d= -f2)
  HIST_TOTAL=$(grep '^TOTAL=' /tmp/worklog_hist_meta_$$.txt 2>/dev/null | cut -d= -f2)
  HIST_HITS=$(grep '^HITS=' /tmp/worklog_hist_meta_$$.txt 2>/dev/null | cut -d= -f2)

  if [ "$EXTENDED" = "True" ]; then
    echo "  ✅ EXTENDED_HISTORY（带时间戳，共扫描 $HIST_TOTAL 条，$LABEL 匹配 $HIST_HITS 条）"
    sed 's|^|    |' /tmp/worklog_hist_$$.txt | head -300
  else
    EXTENDED_HISTORY="false"
    echo "  ⚠️ 未启用 EXTENDED_HISTORY（无法按日期过滤）"
    echo "  以下是 $HIST_FILE 全部最近 200 条命令："
    python3 -c "
import sys
try:
    with open('$HIST_FILE', 'r', encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n') for l in f if l.strip() and not l.startswith('#')]
    for line in lines[-200:]:
        print(line)
except Exception as e:
    print(f'(读取失败: {e})')
" 2>/dev/null | sed 's|^|    |'
  fi

  rm -f /tmp/worklog_hist_$$.txt /tmp/worklog_hist_meta_$$.txt
fi

# ---------- 5. 摘要 ----------
echo ""
echo "=== SUMMARY ==="
echo "  git:     $HAVE_GIT  (提交 $GIT_TOTAL 条)"
echo "  find:    $HAVE_FIND"
echo "  editor:  $HAVE_EDITOR"
echo "  history: $HAVE_HIST  (EXTENDED=$([ "$EXTENDED" = "True" ] && echo true || echo false), file=$HIST_FILE)"
