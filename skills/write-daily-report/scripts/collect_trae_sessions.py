#!/usr/bin/env python3
"""Collect Trae chat sessions within a local-date window.

Trae (ByteDance) is a VSCode fork; session storage lives under
``~/Library/Application Support/Trae/User/…`` (or the CN variant). Reuse
``vscode_fork_common`` for the actual parsing.
"""

from __future__ import annotations

import argparse
import os
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
        description="Collect Trae chat sessions within a local-date window."
    ))
    parser.add_argument("--trae-home", default=None,
                        help="Trae data dir (default: $TRAE_HOME or platform default).")
    args = parser.parse_args()
    try:
        start_date, end_date = resolve_range(args)
    except ValueError as exc:
        return emit_error(f"invalid date: {exc}")
    if end_date < start_date:
        return emit_error("end-date must be >= start-date")
    start, end = local_bounds(start_date, end_date)
    roots = resolve_roots_or_empty(args)

    trae_homes = [Path(args.trae_home).expanduser().resolve()] if args.trae_home else resolve_app_homes("TRAE_HOME", "Trae")

    sessions: list[dict[str, Any]] = []
    start_mtime = start.timestamp()

    for configured_home in trae_homes:
        for home in candidate_workspace_homes(configured_home):
            for workspace_dir in iter_workspace_dirs(home / "User"):
                for session_file in iter_chat_sessions(workspace_dir, start_mtime):
                    session = collect_chat_session(
                    session_file, workspace_dir, roots, start, end,
                    max(1, args.max_messages), max(200, args.max_text_chars),
                    )
                    if session is not None:
                        sessions.append(session)
            # Fallback: some Trae builds keep bubbles in globalStorage/state.vscdb
            # under a different blob prefix. Best-effort scan.
            fallback = collect_global_state_bubbles(
            home / "User", roots, start, end,
            max(1, args.max_messages), max(200, args.max_text_chars),
            blob_prefix="bubbleId:",
            text_fields=("text", "content", "userMessageText"),
            )
            sessions.extend(fallback)

    emit_output(
        "trae", start_date, end_date, start, roots, args.no_filter, sessions,
        extra={"traeHomes": [str(path) for path in trae_homes]},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
