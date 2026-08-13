#!/usr/bin/env python3
"""Collect Cursor chat sessions within a local-date window.

Cursor stores its global chat index and message bubbles in a WAL-mode SQLite
database that is locked while the app runs:

    ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb

  - Table ``composerHeaders``: one row per chat thread. The ``value`` JSON
    carries ``name`` (title), ``subtitle`` (first-message snippet for drafts)
    and ``workspaceIdentifier.uri.fsPath`` (the real project path).
  - Table ``cursorDiskKV`` with keys ``bubbleId:<composerId>:<bubbleId>``:
    message bubbles. ``type`` 1 = user, 2 = assistant; the text lives in the
    top-level ``text`` field (assistant bubbles may start with a <think>…
    </think> block, which is stripped).

To read safely while Cursor is running, the db + -wal + -shm files are copied
to a temp dir first and opened read-only there.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import tempfile
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


THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
BUBBLE_KEY_PREFIX = "bubbleId:"


def default_cursor_home() -> Path:
    return Path(os.environ.get("CURSOR_HOME", "~/Library/Application Support/Cursor"))


def copy_state_db(cursor_home: Path, temp_dir: Path) -> Path | None:
    src = cursor_home / "User" / "globalStorage" / "state.vscdb"
    if not src.is_file():
        return None
    dst = temp_dir / "state.vscdb"
    try:
        shutil.copyfile(src, dst)
        for suffix in ("-wal", "-shm"):
            side = Path(str(src) + suffix)
            if side.is_file():
                shutil.copyfile(side, Path(str(dst) + suffix))
    except OSError:
        return None
    return dst


def open_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def iter_composer_headers(
    conn: sqlite3.Connection, roots: list[Path], start_ms: float, end_ms: float
) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(
            "SELECT composerId, createdAt, lastUpdatedAt, isArchived, isSubagent, value "
            "FROM composerHeaders WHERE isSubagent = 0"
        ).fetchall()
    except sqlite3.Error:
        return []

    headers: list[dict[str, Any]] = []
    for composer_id, created_at, updated_at, is_archived, _is_sub, value in rows:
        try:
            meta = json.loads(value) if value else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
        activity_ms = updated_at or created_at or meta.get("lastUpdatedAt") or meta.get("createdAt")
        if activity_ms is None:
            continue
        if not (start_ms <= activity_ms < end_ms):
            continue
        if is_archived:
            continue
        workspace = (
            (meta.get("workspaceIdentifier") or {}).get("uri") or {}
        ).get("fsPath") or ""
        if workspace and not is_under(workspace, roots):
            continue
        headers.append(
            {
                "composerId": composer_id,
                "name": meta.get("name") or meta.get("subtitle"),
                "cwd": workspace or None,
                "createdAt": created_at,
                "updatedAt": activity_ms,
                "isDraft": bool(meta.get("isDraft")),
            }
        )
    return headers


def iter_bubbles(
    conn: sqlite3.Connection, composer_id: str
) -> dict[str, dict[str, Any]]:
    pattern = f"{BUBBLE_KEY_PREFIX}{composer_id}:%"
    try:
        rows = conn.execute(
            "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?",
            (pattern,),
        ).fetchall()
    except sqlite3.Error:
        return {}
    bubbles: dict[str, dict[str, Any]] = {}
    for key, value in rows:
        if not isinstance(value, (str, bytes)):
            continue
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            bubble_id = key.rsplit(":", 1)[-1]
            bubbles[bubble_id] = parsed
    return bubbles


def read_conversation_order(
    conn: sqlite3.Connection, composer_id: str
) -> list[dict[str, Any]]:
    """Return ``fullConversationHeadersOnly`` from ``composerData:<id>``:
    ordered [{bubbleId, type, createdAt}] with per-bubble timestamps."""
    try:
        row = conn.execute(
            "SELECT value FROM cursorDiskKV WHERE key = ?",
            (f"composerData:{composer_id}",),
        ).fetchone()
    except sqlite3.Error:
        return []
    if not row or not isinstance(row[0], (str, bytes)):
        return []
    try:
        data = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    headers = data.get("fullConversationHeadersOnly")
    if isinstance(headers, list):
        return [h for h in headers if isinstance(h, dict)]
    return []


def bubble_text(bubble: dict[str, Any]) -> str:
    text = bubble.get("text")
    if not isinstance(text, str):
        return ""
    return THINK_RE.sub("", text).strip()


def collect_composer(
    conn: sqlite3.Connection, header: dict[str, Any],
    start: Any, end: Any,
    max_messages: int, max_text_chars: int,
) -> dict[str, Any] | None:
    # Per-bubble timestamps live in composerData.fullConversationHeadersOnly;
    # bubble bodies live at bubbleId:<composerId>:<bubbleId>. Composers whose
    # header activity is in-window but whose bubbles all predate the window
    # drop out here, which is exactly what a daily report wants.
    order = read_conversation_order(conn, header["composerId"])
    bubbles = iter_bubbles(conn, header["composerId"])

    messages: list[dict[str, Any]] = []
    first_activity = None
    last_activity = None

    if order:
        sequence = order
    else:
        # No ordering metadata: fall back to all bubbles with no timestamps.
        sequence = [
            {"bubbleId": bid, "type": b.get("type"), "createdAt": None}
            for bid, b in bubbles.items()
        ]

    for item in sequence:
        bubble_id = item.get("bubbleId")
        bubble = bubbles.get(bubble_id) if isinstance(bubble_id, str) else None
        if bubble is None:
            continue
        bubble_type = item.get("type") or bubble.get("type")
        if bubble_type == 1:
            role = "user"
        elif bubble_type == 2:
            role = "assistant"
        else:
            continue
        timestamp = parse_timestamp(item.get("createdAt"))
        if timestamp is not None and not (start <= timestamp < end):
            continue
        text_value = redact(bubble_text(bubble))
        if not text_value:
            continue
        anchor = timestamp or parse_timestamp(header["updatedAt"])
        first_activity = anchor if first_activity is None else min(first_activity, anchor)
        last_activity = anchor if last_activity is None else max(last_activity, anchor)
        messages.append(make_message(role, anchor, text_value, max_text_chars))

    if not messages:
        return None
    messages, truncated = truncate_messages(messages, max_messages)
    return make_session(
        session_id=header["composerId"],
        title=header.get("name"),
        cwd=header.get("cwd"),
        messages=messages,
        truncated=truncated,
        source="cursor:state.vscdb",
        first_activity=first_activity,
        last_activity=last_activity,
    )


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(
        description="Collect Cursor chat sessions within a local-date window."
    ))
    parser.add_argument("--cursor-home", default=None,
                        help="Cursor data dir (default: $CURSOR_HOME or "
                             "~/Library/Application Support/Cursor).")
    args = parser.parse_args()
    try:
        start_date, end_date = resolve_range(args)
    except ValueError as exc:
        return emit_error(f"invalid date: {exc}")
    if end_date < start_date:
        return emit_error("end-date must be >= start-date")
    start, end = local_bounds(start_date, end_date)
    roots = resolve_roots_or_empty(args)

    cursor_home = (
        Path(args.cursor_home).expanduser().resolve()
        if args.cursor_home
        else default_cursor_home().expanduser().resolve()
    )

    sessions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="daily-report-cursor-") as tmp:
        db_copy = copy_state_db(cursor_home, Path(tmp))
        if db_copy is not None:
            try:
                conn = open_readonly(db_copy)
            except sqlite3.Error as exc:
                return emit_error(f"cannot open Cursor state.vscdb: {exc}")
            with conn:
                start_ms = start.timestamp() * 1000
                end_ms = end.timestamp() * 1000
                for header in iter_composer_headers(conn, roots, start_ms, end_ms):
                    session = collect_composer(
                        conn, header, start, end,
                        max(1, args.max_messages), max(200, args.max_text_chars),
                    )
                    if session is not None:
                        sessions.append(session)

    emit_output(
        "cursor", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={"cursorHome": str(cursor_home)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
