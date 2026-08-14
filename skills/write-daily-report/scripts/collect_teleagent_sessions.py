#!/usr/bin/env python3
"""Collect TeleAgent daily-log entries within a local-date window.

Default path: ~/.local/share/TeleAgent/memory/daily-log/YYYY-MM-DD.md
Each line is `- [ISO8601 timestamp] description`.
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from collector_common import (
    add_common_args,
    emit_error,
    emit_output,
    make_message,
    make_session,
    parse_timestamp,
    redact,
    resolve_range,
    resolve_roots_or_empty,
)
from platform_paths import app_homes


ENTRY_RE = re.compile(r"^-\s*\[(?P<ts>[^\]]+)\]\s*(?P<text>.+?)\s*$")


def iter_log_files(log_dir: Path, start_date, end_date) -> list[tuple[Any, Path]]:
    if not log_dir.is_dir():
        return []
    files: list[tuple[Any, Path]] = []
    current = start_date
    while current <= end_date:
        candidate = log_dir / f"{current.isoformat()}.md"
        if candidate.is_file():
            files.append((current, candidate))
        from datetime import timedelta
        current += timedelta(days=1)
    return files


def collect_file(log_file: Path, log_date, start: datetime, end: datetime,
                 max_text_chars: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return entries
    for line in text.splitlines():
        match = ENTRY_RE.match(line)
        if not match:
            continue
        timestamp = parse_timestamp(match.group("ts"))
        if timestamp is None or not (start <= timestamp < end):
            continue
        body = redact(match.group("text").strip())
        if not body:
            continue
        entries.append(make_message("assistant", timestamp, body, max_text_chars))
    return entries


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(
        description="Collect TeleAgent daily-log entries within a local-date window."
    ))
    parser.add_argument("--teleagent-home", default=None,
                        help="TeleAgent data dir (default: override or platform default).")
    parser.add_argument("--daily-log-dir", default=os.environ.get("TELEAGENT_DAILY_LOG_DIR"))
    args = parser.parse_args()
    try:
        start_date, end_date = resolve_range(args)
    except ValueError as exc:
        return emit_error(f"invalid date: {exc}")
    if end_date < start_date:
        return emit_error("end-date must be >= start-date")
    from collector_common import local_bounds
    start, end = local_bounds(start_date, end_date)
    roots = resolve_roots_or_empty(args)

    teleagent_homes = [Path(args.teleagent_home).expanduser().resolve()] if args.teleagent_home else app_homes(
        "TELEAGENT_HOME", "TeleAgent"
    )
    if not os.environ.get("TELEAGENT_HOME") and not os.environ.get("TELEAGENT_DIR") and os.name != "nt":
        teleagent_homes = [Path("~/.local/share/TeleAgent").expanduser()]
    if os.environ.get("TELEAGENT_DIR") and not os.environ.get("TELEAGENT_HOME"):
        teleagent_homes = [Path(os.environ["TELEAGENT_DIR"])]
    log_dirs = [
        Path(args.daily_log_dir).expanduser().resolve()
        if args.daily_log_dir
        else home.expanduser().resolve() / "memory" / "daily-log"
        for home in teleagent_homes
    ]

    days: list[dict[str, Any]] = []
    all_entries: list[dict[str, Any]] = []
    for log_dir in log_dirs:
        for log_date, log_file in iter_log_files(log_dir, start_date, end_date):
            entries = collect_file(log_file, log_date, start, end, max(200, args.max_text_chars))
            if not entries:
                continue
            days.append({"date": log_date.isoformat(), "file": str(log_file),
                         "entryCount": len(entries), "entries": entries})
            all_entries.extend(entries)

    sessions: list[dict[str, Any]] = []
    if all_entries:
        sessions.append(make_session(
            session_id=f"teleagent-daily-log-{start_date.isoformat()}",
            title="TeleAgent daily log",
            cwd=None,
            messages=all_entries,
            truncated=False,
            source=",".join(str(log_dir) for log_dir in log_dirs),
            first_activity=parse_timestamp(all_entries[0]["timestamp"]),
            last_activity=parse_timestamp(all_entries[-1]["timestamp"]),
        ))

    emit_output(
        "teleagent", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={
            "dailyLogDirs": [str(log_dir) for log_dir in log_dirs],
            "daysWithEntries": len(days),
            "totalEntries": len(all_entries),
            "days": days,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
