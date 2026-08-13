#!/usr/bin/env python3
"""Shared logic for VSCode-fork chat collectors (Trae, Qoder, ...).

Both Trae (ByteDance) and Qoder (Alibaba) are VSCode forks that store chat
sessions as JSON files alongside their workspace folders:

    <app>/User/workspaceStorage/<workspace-id>/workspace.json     # folder URI
    <app>/User/workspaceStorage/<workspace-id>/chatSessions/<session-id>.json

The ``chatSessions`` JSON shape mirrors VSCode 1.93+ ChatModel:

  {
    "version": 2,
    "sessionId": "...",
    "creationDate": 1700000000000,    # ms epoch
    "lastMessageDate": 1700001000000, # ms epoch (optional)
    "customTitle": "...",              # user-given title
    "requests": [
      {
        "requestId": "...",
        "timestamp": 1700000000000,    # ms epoch
        "message": {"text": "user prompt", "parts": [...]},
        "response": [{"value": "assistant markdown..."}, ...],
        "modelId": "...",
        "agent": {...}
      },
      ...
    ]
  }

We extract text defensively from ``message.text``/``message.parts`` for the
user side and from every ``response[*].value`` string for the assistant side,
filtering by the per-request timestamp window.
"""

from __future__ import annotations

import json
import os
import sqlite3
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from collector_common import (
    is_under,
    make_message,
    make_session,
    parse_timestamp,
    redact,
    truncate_messages,
)


def candidate_workspace_homes(app_home: Path) -> list[Path]:
    """Return candidate Application Support directories in priority order.

    Trae has both international and CN builds; Qoder ships a single build. We
    probe a few well-known names so a single collector script works for both.
    """
    candidates = []
    seen: set[Path] = set()
    for raw in [
        app_home,
        app_home.parent / f"{app_home.name} CN",
        app_home.parent / f"{app_home.name}-CN",
        Path.home() / f".{app_home.name.lower()}",
        Path.home() / f".{app_home.name.lower()}-cn",
    ]:
        try:
            path = raw.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if path in seen:
            continue
        seen.add(path)
        candidates.append(path)
    return candidates


def read_workspace_folder(workspace_json: Path) -> str | None:
    try:
        data = json.loads(workspace_json.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    folder = data.get("folder")
    if not isinstance(folder, str):
        return None
    if folder.startswith("file://"):
        from urllib.parse import unquote
        return unquote(folder[len("file://"):])
    return folder


def extract_user_text(message: dict[str, Any]) -> str:
    if not isinstance(message, dict):
        return ""
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text
    parts = message.get("parts")
    if isinstance(parts, list):
        chunks: list[str] = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
            elif isinstance(part, str):
                chunks.append(part)
        return "\n".join(chunks).strip()
    return ""


def extract_assistant_text(response: Any) -> str:
    """VSCode stores response parts as a list of `{kind, value}` objects. Pull
    the string ``value`` field from any part that looks like a text reply."""
    if not isinstance(response, list):
        return ""
    chunks: list[str] = []
    for part in response:
        if not isinstance(part, dict):
            continue
        kind = part.get("kind")
        if kind and kind not in {"markdown", "text", "reply", "message", None}:
            continue  # tool invocations, edits, etc.
        value = part.get("value")
        if isinstance(value, str) and value.strip():
            chunks.append(value)
    return "\n".join(chunks).strip()


def iter_workspace_dirs(user_home: Path) -> list[Path]:
    ws_root = user_home / "workspaceStorage"
    if not ws_root.is_dir():
        return []
    return sorted(path for path in ws_root.iterdir() if path.is_dir())


def iter_chat_sessions(workspace_dir: Path, start_mtime: float) -> list[Path]:
    sessions_dir = workspace_dir / "chatSessions"
    if not sessions_dir.is_dir():
        return []
    candidates: list[Path] = []
    for path in sessions_dir.glob("*.json"):
        try:
            if path.stat().st_mtime < start_mtime:
                continue
        except OSError:
            continue
        candidates.append(path)
    return sorted(candidates)


def collect_chat_session(
    session_file: Path,
    workspace_dir: Path,
    roots: list[Path],
    start: datetime,
    end: datetime,
    max_messages: int,
    max_text_chars: int,
) -> dict[str, Any] | None:
    try:
        data = json.loads(session_file.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    workspace_json = workspace_dir / "workspace.json"
    cwd = read_workspace_folder(workspace_json) if workspace_json.is_file() else None
    if cwd and not is_under(cwd, roots):
        return None

    creation = parse_timestamp(data.get("creationDate"))
    last_msg = parse_timestamp(data.get("lastMessageDate"))
    title = data.get("customTitle") or data.get("title")
    session_id = data.get("sessionId") or session_file.stem

    messages: list[dict[str, Any]] = []
    first_activity = None
    last_activity = None
    for request in data.get("requests") or []:
        if not isinstance(request, dict):
            continue
        timestamp = parse_timestamp(request.get("timestamp")) or creation
        if timestamp is None or not (start <= timestamp < end):
            continue
        user_text = redact(extract_user_text(request.get("message") or {}))
        if user_text:
            messages.append(make_message("user", timestamp, user_text, max_text_chars))
        assistant_text = redact(extract_assistant_text(request.get("response")))
        if assistant_text:
            messages.append(make_message("assistant", timestamp, assistant_text, max_text_chars))
        if messages:
            first_activity = timestamp if first_activity is None else min(first_activity, timestamp)
            last_activity = timestamp if last_activity is None else max(last_activity, timestamp)

    if first_activity is None:
        return None
    messages, truncated = truncate_messages(messages, max_messages)
    return make_session(
        session_id=session_id,
        title=title,
        cwd=str(Path(cwd).expanduser()) if cwd else None,
        messages=messages,
        truncated=truncated,
        source=str(session_file),
        first_activity=first_activity,
        last_activity=last_activity or last_msg,
    )


def collect_global_state_bubbles(
    user_home: Path, roots: list[Path], start: datetime, end: datetime,
    max_messages: int, max_text_chars: int,
    blob_prefix: str, text_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Fallback for fork builds that store bubbles in
    ``globalStorage/state.vscdb::cursorDiskKV`` with a different prefix.
    Mirrors the Cursor strategy: copy db to tempdir, open read-only."""
    src = user_home / "globalStorage" / "state.vscdb"
    if not src.is_file():
        return []
    sessions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="daily-report-fork-") as tmp:
        dst = Path(tmp) / "state.vscdb"
        try:
            shutil.copyfile(src, dst)
            for suffix in ("-wal", "-shm"):
                side = Path(str(src) + suffix)
                if side.is_file():
                    shutil.copyfile(side, Path(str(dst) + suffix))
        except OSError:
            return []
        try:
            conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
        except sqlite3.Error:
            return []
        with conn:
            try:
                rows = conn.execute(
                    "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?",
                    (f"{blob_prefix}%",),
                ).fetchall()
            except sqlite3.Error:
                return []
            grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
            for key, value in rows:
                if not isinstance(value, (str, bytes)):
                    continue
                try:
                    parsed = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(parsed, dict):
                    continue
                parts = key.split(":", 2)
                if len(parts) < 3:
                    continue
                grouped.setdefault(parts[1], []).append((parts[2], parsed))
            for composer_id, bubbles in grouped.items():
                msgs: list[dict[str, Any]] = []
                for _bid, bubble in bubbles:
                    bubble_type = bubble.get("type")
                    role = "user" if bubble_type == 1 else "assistant" if bubble_type == 2 else None
                    if role is None:
                        continue
                    text = ""
                    for field in text_fields:
                        value = bubble.get(field)
                        if isinstance(value, str) and value.strip():
                            text = value.strip()
                            break
                    if not text:
                        continue
                    msgs.append(make_message(role, start, redact(text), max_text_chars))
                if not msgs:
                    continue
                msgs, truncated = truncate_messages(msgs, max_messages)
                sessions.append(make_session(
                    session_id=composer_id,
                    title=None,
                    cwd=None,
                    messages=msgs,
                    truncated=truncated,
                    source=str(src),
                    first_activity=start,
                    last_activity=end,
                ))
    return sessions


def resolve_app_home(env_var: str, default_dirname: str) -> Path:
    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / "Library" / "Application Support" / default_dirname).expanduser().resolve()
