#!/usr/bin/env python3
"""Collect Pi Agent text messages within a local-date window."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

from collector_common import (
    add_common_args,
    emit_error,
    emit_output,
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


SECRET_PLACEHOLDER = "[REDACTED]"


def read_header(transcript: Path) -> dict[str, Any] | None:
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as source:
            for line in source:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (
                    isinstance(record, dict)
                    and record.get("type") == "session"
                    and isinstance(record.get("id"), str)
                    and isinstance(record.get("cwd"), str)
                ):
                    return record
                return None
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return None


def iter_session_files(session_dir: Path) -> Iterable[Path]:
    if not session_dir.is_dir():
        return
    yield from sorted(session_dir.glob("*.jsonl"))
    try:
        project_dirs = sorted(path for path in session_dir.iterdir() if path.is_dir())
    except OSError:
        return
    for project_dir in project_dirs:
        yield from sorted(project_dir.glob("*.jsonl"))


def active_branch(entries: list[dict[str, Any]], version: int) -> list[dict[str, Any]]:
    if version < 2 or not entries:
        return entries
    indexed = {
        entry["id"]: entry
        for entry in entries
        if isinstance(entry.get("id"), str) and entry["id"]
    }
    leaf = next(
        (entry for entry in reversed(entries)
         if isinstance(entry.get("id"), str) and entry["id"] in indexed),
        None,
    )
    if leaf is None:
        return entries
    path: list[dict[str, Any]] = []
    seen: set[str] = set()
    current: dict[str, Any] | None = leaf
    while current is not None:
        entry_id = current.get("id")
        if not isinstance(entry_id, str) or entry_id in seen:
            return entries
        seen.add(entry_id)
        path.append(current)
        parent_id = current.get("parentId")
        current = indexed.get(parent_id) if isinstance(parent_id, str) else None
    path.reverse()
    return path


def collect_file(
    transcript: Path, roots: list[Path],
    start: Any, end: Any,
    max_messages: int, max_text_chars: int,
    header: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    verified_header = header or read_header(transcript)
    if verified_header is None or not is_under(verified_header["cwd"], roots):
        return None

    entries: list[dict[str, Any]] = []
    try:
        source = transcript.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return None
    with source:
        for line_number, line in enumerate(source):
            if line_number == 0 and line.strip():
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(record, dict) and record.get("type") != "session":
                entries.append(record)

    try:
        version = int(verified_header.get("version", 1))
    except (TypeError, ValueError):
        version = 1
    branch_entries = active_branch(entries, version)

    title: str | None = None
    for entry in entries:
        if entry.get("type") == "session_info" and isinstance(entry.get("name"), str):
            title = entry["name"].strip() or None

    first_activity = None
    last_activity = None
    messages: list[dict[str, Any]] = []
    for entry in branch_entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue
        timestamp = parse_timestamp(message.get("timestamp")) or parse_timestamp(entry.get("timestamp"))
        if timestamp is None or not (start <= timestamp < end):
            continue
        text_value = redact(_extract_message_text(message.get("content")).strip())
        if not text_value:
            continue
        first_activity = timestamp if first_activity is None else min(first_activity, timestamp)
        last_activity = timestamp if last_activity is None else max(last_activity, timestamp)
        messages.append(make_message(role, timestamp, text_value, max_text_chars))

    if first_activity is None:
        return None

    messages, truncated = truncate_messages(messages, max_messages)
    parent_session = verified_header.get("parentSession")
    return make_session(
        session_id=verified_header["id"],
        title=title,
        cwd=str(Path(verified_header["cwd"]).expanduser()),
        messages=messages,
        truncated=truncated,
        source=str(transcript),
        parent_session=parent_session if isinstance(parent_session, str) else None,
        first_activity=first_activity,
        last_activity=last_activity,
    )


def _extract_message_text(content: Any) -> str:
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


def candidate_transcripts(session_dir: Path, roots: list[Path], start_mtime: float) -> list[tuple[Path, dict[str, Any]]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for transcript in iter_session_files(session_dir):
        try:
            if transcript.stat().st_mtime < start_mtime:
                continue
        except OSError:
            continue
        header = read_header(transcript)
        if header is None or not is_under(header["cwd"], roots):
            continue
        candidates.append((transcript, header))
    return candidates


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(
        description="Collect Pi Agent sessions active within a local-date window."
    ))
    parser.add_argument(
        "--pi-home",
        default=os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent"),
    )
    parser.add_argument(
        "--session-dir",
        default=os.environ.get("PI_CODING_AGENT_SESSION_DIR"),
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

    pi_home = Path(args.pi_home).expanduser().resolve()
    session_dir = (
        Path(args.session_dir).expanduser().resolve()
        if args.session_dir
        else pi_home / "sessions"
    )

    sessions: list[dict[str, Any]] = []
    for transcript, header in candidate_transcripts(session_dir, roots, start.timestamp()):
        session = collect_file(
            transcript, roots, start, end,
            max(1, args.max_messages), max(200, args.max_text_chars),
            header,
        )
        if session is not None:
            sessions.append(session)

    emit_output(
        "pi", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={"sessionDir": str(session_dir)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
