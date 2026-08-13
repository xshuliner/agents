#!/usr/bin/env python3
"""Collect Codex Desktop rollout sessions within a local-date window.

Codex Desktop stores one JSONL per thread under:

    ${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-*.jsonl

The first record is ``session_meta`` with the real cwd. Subsequent records
are ``event_msg`` (lifecycle) or ``response_item`` with payload.type
``message`` (role=user|assistant|developer), ``function_call`` and
``function_call_output`` (skipped here).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

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


def iter_rollout_files(codex_home: Path, start_mtime: float) -> list[Path]:
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.is_dir():
        return []
    candidates: list[Path] = []
    for path in sessions_dir.rglob("rollout-*.jsonl"):
        try:
            if path.stat().st_mtime < start_mtime:
                continue
        except OSError:
            continue
        candidates.append(path)
    return sorted(candidates)


def read_session_meta(transcript: Path) -> dict[str, Any] | None:
    """Read the first ``session_meta`` record; abort early if cwd fails whitelist."""
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as source:
            for line in source:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    return None
                if isinstance(record, dict) and record.get("type") == "session_meta":
                    payload = record.get("payload") or {}
                    return {
                        "cwd": payload.get("cwd"),
                        "session_id": payload.get("id") or payload.get("session_id"),
                        "originator": payload.get("originator"),
                        "model_provider": payload.get("model_provider"),
                        "created_at": parse_timestamp(record.get("timestamp") or payload.get("timestamp")),
                    }
                return None
    except OSError:
        return None
    return None


def extract_message_text(content: Any) -> str:
    """Codex encodes message content as a list of parts with ``input_text`` /
    ``output_text`` or free-form text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for part in content:
        if isinstance(part, str):
            chunks.append(part)
        elif isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def collect_file(
    transcript: Path, roots: list[Path],
    start: Any, end: Any,
    max_messages: int, max_text_chars: int,
) -> dict[str, Any] | None:
    meta = read_session_meta(transcript)
    if meta is None:
        return None
    cwd = meta.get("cwd")
    if not cwd or not is_under(cwd, roots):
        return None

    first_activity = None
    last_activity = None
    messages: list[dict[str, Any]] = []
    session_id = meta.get("session_id") or transcript.stem
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as source:
            for line in source:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("type") != "response_item":
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict) or payload.get("type") != "message":
                    continue
                role = payload.get("role")
                if role not in {"user", "assistant"}:
                    continue
                timestamp = parse_timestamp(record.get("timestamp")) or parse_timestamp(payload.get("timestamp"))
                if timestamp is None or not (start <= timestamp < end):
                    continue
                text_value = redact(extract_message_text(payload.get("content")))
                if not text_value:
                    continue
                first_activity = timestamp if first_activity is None else min(first_activity, timestamp)
                last_activity = timestamp if last_activity is None else max(last_activity, timestamp)
                messages.append(make_message(role, timestamp, text_value, max_text_chars))
    except OSError:
        return None

    if first_activity is None:
        return None

    messages, truncated = truncate_messages(messages, max_messages)
    title_path = Path(cwd).name if cwd else None
    return make_session(
        session_id=session_id,
        title=title_path,
        cwd=str(Path(cwd).expanduser()),
        messages=messages,
        truncated=truncated,
        source=str(transcript),
        first_activity=first_activity,
        last_activity=last_activity,
    )


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(
        description="Collect Codex Desktop rollout sessions within a local-date window."
    ))
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", "~/.codex"),
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

    codex_home = Path(args.codex_home).expanduser().resolve()

    sessions: list[dict[str, Any]] = []
    for transcript in iter_rollout_files(codex_home, start.timestamp()):
        session = collect_file(
            transcript, roots, start, end,
            max(1, args.max_messages), max(200, args.max_text_chars),
        )
        if session is not None:
            sessions.append(session)

    emit_output(
        "codex", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={"codexHome": str(codex_home)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
