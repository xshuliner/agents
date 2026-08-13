#!/usr/bin/env python3
"""Collect Claude Code text messages within a local-date window."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from collector_common import (
    add_common_args,
    clip_text,
    emit_error,
    emit_output,
    extract_text_blocks,
    is_under,
    local_bounds,
    make_message,
    make_session,
    parse_timestamp,
    redact,
    resolve_range,
    resolve_roots_or_empty,
    truncate_messages,
)


def collect_file(
    transcript: Path,
    roots: list[Path],
    start: Any,
    end: Any,
    max_messages: int,
    max_text_chars: int,
) -> dict[str, Any] | None:
    session_id = transcript.stem
    cwd = ""
    branch = ""
    title = ""
    first_activity = None
    last_activity = None
    messages: list[dict[str, Any]] = []

    try:
        source = transcript.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return None

    with source:
        for line in source:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(record, dict):
                continue
            if not title and isinstance(record.get("aiTitle"), str):
                title = record["aiTitle"].strip()
            if isinstance(record.get("cwd"), str) and record["cwd"]:
                cwd = record["cwd"]
            if isinstance(record.get("gitBranch"), str) and record["gitBranch"]:
                branch = record["gitBranch"]
            if isinstance(record.get("sessionId"), str) and record["sessionId"]:
                session_id = record["sessionId"]

            timestamp = parse_timestamp(record.get("timestamp"))
            if timestamp is None or not (start <= timestamp < end):
                continue
            first_activity = timestamp if first_activity is None else min(first_activity, timestamp)
            last_activity = timestamp if last_activity is None else max(last_activity, timestamp)

            record_type = record.get("type")
            if record_type not in {"user", "assistant"} or record.get("isSidechain") is True:
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            text_value = redact(extract_text_blocks(message.get("content")).strip())
            if not text_value:
                continue
            messages.append(make_message(record_type, timestamp, text_value, max_text_chars))

    if first_activity is None or not cwd or not is_under(cwd, roots):
        return None

    messages, truncated = truncate_messages(messages, max_messages)
    return make_session(
        session_id=session_id,
        title=title or None,
        cwd=str(Path(cwd).expanduser()),
        messages=messages,
        truncated=truncated,
        source=str(transcript),
        git_branch=branch or None,
        first_activity=first_activity,
        last_activity=last_activity,
    )


def candidate_transcripts(projects: Path, roots: list[Path], start_mtime: float) -> list[Path]:
    candidates: set[Path] = set()
    if not roots:
        for project_dir in projects.iterdir():
            if not project_dir.is_dir():
                continue
            for transcript in project_dir.rglob("*.jsonl"):
                if "subagents" in transcript.parts:
                    continue
                try:
                    if transcript.stat().st_mtime < start_mtime:
                        continue
                except OSError:
                    continue
                candidates.add(transcript)
        return sorted(candidates)
    for root in roots:
        encoded_prefix = str(root).replace(os.sep, "-")
        for project_dir in projects.glob(encoded_prefix + "*"):
            if not project_dir.is_dir():
                continue
            for transcript in project_dir.rglob("*.jsonl"):
                if "subagents" in transcript.parts:
                    continue
                try:
                    if transcript.stat().st_mtime < start_mtime:
                        continue
                except OSError:
                    continue
                candidates.add(transcript)
    return sorted(candidates)


def main() -> int:
    parser = add_common_args(__import__("argparse").ArgumentParser(
        description="Collect Claude Code sessions active within a local-date window."
    ))
    parser.add_argument(
        "--claude-home",
        default=os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"),
    )
    args = parser.parse_args()
    try:
        start_date, end_date = resolve_range(args)
    except ValueError as exc:
        return emit_error(f"invalid date: {exc}")
    if end_date < start_date:
        return emit_error("end-date must be >= start-date")
    start, end = local_bounds(start_date, end_date)
    roots = resolve_roots_or_empty(args)

    claude_home = Path(args.claude_home).expanduser().resolve()
    projects = claude_home / "projects"

    sessions: list[dict[str, Any]] = []
    if projects.is_dir():
        for transcript in candidate_transcripts(projects, roots, start.timestamp()):
            session = collect_file(
                transcript, roots, start, end,
                max(1, args.max_messages), max(200, args.max_text_chars),
            )
            if session is not None:
                sessions.append(session)

    emit_output("claude", start_date, end_date, start, roots, args.no_filter, sessions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
