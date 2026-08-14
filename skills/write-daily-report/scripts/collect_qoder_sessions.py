#!/usr/bin/env python3
"""Collect Qoder chat sessions within a local-date window.

Qoder (Alibaba) is a VSCode fork; session storage lives under
``~/Library/Application Support/Qoder/User/…``. Reuses the same VSCode-fork
chatSession parsing as Trae.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from collector_common import (
    add_common_args,
    emit_error,
    emit_output,
    local_bounds,
    resolve_range,
    resolve_roots_or_empty,
)
from vscode_fork_common import (
    candidate_workspace_homes,
    collect_chat_session,
    collect_global_state_bubbles,
    iter_chat_sessions,
    iter_workspace_dirs,
    resolve_app_homes,
)


def main() -> int:
    parser = add_common_args(argparse.ArgumentParser(
        description="Collect Qoder chat sessions within a local-date window."
    ))
    parser.add_argument("--qoder-home", default=None,
                        help="Qoder data dir (default: $QODER_HOME or platform default).")
    args = parser.parse_args()
    try:
        start_date, end_date = resolve_range(args)
    except ValueError as exc:
        return emit_error(f"invalid date: {exc}")
    if end_date < start_date:
        return emit_error("end-date must be >= start-date")
    start, end = local_bounds(start_date, end_date)
    roots = resolve_roots_or_empty(args)

    qoder_homes = [Path(args.qoder_home).expanduser().resolve()] if args.qoder_home else resolve_app_homes("QODER_HOME", "Qoder")

    sessions: list[dict[str, Any]] = []
    start_mtime = start.timestamp()

    for configured_home in qoder_homes:
        for home in candidate_workspace_homes(configured_home):
            for workspace_dir in iter_workspace_dirs(home / "User"):
                for session_file in iter_chat_sessions(workspace_dir, start_mtime):
                    session = collect_chat_session(
                        session_file, workspace_dir, roots, start, end,
                        max(1, args.max_messages), max(200, args.max_text_chars),
                    )
                    if session is not None:
                        sessions.append(session)
            fallback = collect_global_state_bubbles(
                home / "User", roots, start, end,
                max(1, args.max_messages), max(200, args.max_text_chars),
                blob_prefix="bubbleId:",
                text_fields=("text", "content", "userMessageText"),
            )
            sessions.extend(fallback)

    emit_output(
        "qoder", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={"qoderHomes": [str(path) for path in qoder_homes]},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
