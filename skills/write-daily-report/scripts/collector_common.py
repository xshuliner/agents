#!/usr/bin/env python3
"""Shared helpers for all daily/weekly report session collectors.

Every collector emits the same JSON envelope so downstream merging stays
uniform:

{
  "schemaVersion": 1,
  "source": "<source-name>",
  "date": "YYYY-MM-DD" | null,         # single-day only
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "timezone": "CST",
  "workRoots": [...],
  "noFilter": bool,
  "sessionCount": N,
  "sessions": [
    {
      "sessionId": "...",
      "title": "..." | null,
      "cwd": "..." | null,
      "gitBranch": "..." | null,
      "parentSession": "..." | null,
      "firstActivityAt": iso | null,
      "updatedAt": iso | null,
      "messages": [{"role": "user"|"assistant", "timestamp": iso, "text": "..."}],
      "messagesTruncated": bool,
      "source": "<path-or-origin>"
    }
  ],
  ... source-specific extras ...
}

Adding a new source:
1. Copy the smallest existing collector (e.g. collect_teleagent_sessions.py).
2. Reuse add_common_args / resolve_range / local_bounds / redact /
   truncate_messages / emit_output from this module.
3. Only implement source-specific discovery + message extraction.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from work_roots import resolve_work_roots


SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|token|password|secret|cookie)"
        r"(\s*[:=]\s*)['\"]?[^\s'\",}]+"
    ),
)


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach the shared CLI surface every collector exposes."""
    parser.add_argument("--date", dest="day", default=None,
                        help="Target local date YYYY-MM-DD (default: today).")
    parser.add_argument("--start-date", dest="start_date", default=None,
                        help="Range start (inclusive) YYYY-MM-DD. Overrides --date.")
    parser.add_argument("--end-date", dest="end_date", default=None,
                        help="Range end (inclusive) YYYY-MM-DD. Defaults to start-date.")
    parser.add_argument(
        "--work-root",
        action="append",
        default=None,
        help=(
            "Approved cwd root; repeat for multiple roots. If omitted, read the "
            "OS-path-separated DAILY_REPORT_WORK_ROOTS environment variable."
        ),
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Summary mode: skip directory whitelist and collect all sessions.",
    )
    parser.add_argument("--max-messages", type=int, default=80,
                        help="Max messages kept per session (head/tail sampling).")
    parser.add_argument("--max-text-chars", type=int, default=4000,
                        help="Per-message text truncation limit.")
    return parser


def resolve_range(args: argparse.Namespace) -> tuple[date, date]:
    if args.start_date:
        start = date.fromisoformat(args.start_date)
        end = date.fromisoformat(args.end_date) if args.end_date else start
        return start, end
    if args.day:
        selected = date.fromisoformat(args.day)
        return selected, selected
    today = date.today()
    return today, today


def local_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Inclusive start-date through inclusive end-date as a local [start, end) window."""
    timezone = datetime.now().astimezone().tzinfo
    start = datetime.combine(start_date, time.min, tzinfo=timezone)
    end = datetime.combine(end_date, time.min, tzinfo=timezone) + timedelta(days=1)
    return start, end


def parse_timestamp(value: Any) -> datetime | None:
    """Accept epoch seconds/ms or ISO-8601 strings; always return local tz-aware."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=datetime.now().astimezone().tzinfo)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed.astimezone()


def redact(text_value: str) -> str:
    redacted = text_value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def extract_text_blocks(content: Any) -> str:
    """Pull text out of string-or-block-list message content."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            value = block.get("text")
            if isinstance(value, str):
                chunks.append(value)
    return "\n".join(chunks)


def is_under(path_text: str, roots: list[Path]) -> bool:
    """Empty roots == no-filter mode: accept everything."""
    if not roots:
        return True
    try:
        candidate = Path(path_text).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    for root in roots:
        try:
            candidate.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def resolve_roots_or_empty(args: argparse.Namespace) -> list[Path]:
    """Shared --work-root / --no-filter handling."""
    if getattr(args, "no_filter", False):
        return []
    return resolve_work_roots(getattr(args, "work_root", None), allow_empty=True)


def truncate_messages(
    messages: list[dict[str, Any]], max_messages: int
) -> tuple[list[dict[str, Any]], bool]:
    """Keep head + tail when a session overflows, so both the original goal and
    the final state survive."""
    if len(messages) <= max_messages:
        return messages, False
    head_count = min(4, max_messages // 4)
    return messages[:head_count] + messages[-(max_messages - head_count):], True


def clip_text(text_value: str, max_text_chars: int) -> str:
    if len(text_value) > max_text_chars:
        return text_value[:max_text_chars] + "…"
    return text_value


def make_message(role: str, timestamp: datetime, text_value: str,
                 max_text_chars: int) -> dict[str, Any]:
    return {
        "role": role,
        "timestamp": timestamp.isoformat(),
        "text": clip_text(text_value, max(200, max_text_chars)),
    }


def make_session(
    session_id: str,
    title: str | None,
    cwd: str | None,
    messages: list[dict[str, Any]],
    truncated: bool,
    source: str,
    git_branch: str | None = None,
    parent_session: str | None = None,
    first_activity: datetime | None = None,
    last_activity: datetime | None = None,
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "title": title,
        "cwd": cwd,
        "gitBranch": git_branch,
        "parentSession": parent_session,
        "firstActivityAt": first_activity.isoformat() if first_activity else None,
        "updatedAt": last_activity.isoformat() if last_activity else None,
        "messages": messages,
        "messagesTruncated": truncated,
        "source": source,
    }


def emit_output(
    source: str,
    start_date: date,
    end_date: date,
    timezone_start: datetime,
    roots: list[Path],
    no_filter: bool,
    sessions: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> None:
    sessions.sort(key=lambda item: (item.get("updatedAt") or "", item["sessionId"]))
    output: dict[str, Any] = {
        "schemaVersion": 1,
        "source": source,
        "date": start_date.isoformat() if start_date == end_date else None,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "timezone": str(timezone_start.tzinfo),
        "workRoots": [str(root) for root in roots],
        "noFilter": no_filter,
        "sessionCount": len(sessions),
        "sessions": sessions,
    }
    if extra:
        output.update(extra)
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def emit_error(message: str) -> int:
    print(json.dumps({"error": message}, ensure_ascii=False))
    return 2
