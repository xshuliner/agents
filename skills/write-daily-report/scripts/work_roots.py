#!/usr/bin/env python3
"""Resolve approved work roots without relying on a personal default path."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path


ENV_NAME = "DAILY_REPORT_WORK_ROOTS"


def resolve_work_roots(
    cli_values: Iterable[str] | None,
    environ: Mapping[str, str] | None = None,
    allow_empty: bool = False,
) -> list[Path]:
    """Prefer explicit CLI values, then an OS-path-separated environment value.

    When ``allow_empty`` is True and no roots are configured, returns an empty
    list (summary / no-filter mode). Otherwise raises ValueError.
    """
    values = [value.strip() for value in (cli_values or []) if value.strip()]
    environment = os.environ if environ is None else environ
    if not values:
        configured = environment.get(ENV_NAME, "")
        values = [
            value.strip()
            for value in configured.split(os.pathsep)
            if value.strip()
        ]
    if not values:
        if allow_empty:
            return []
        raise ValueError(
            "no work roots configured; pass --work-root (repeatable), set "
            f"{ENV_NAME} using the OS path separator, or use --no-filter for "
            "summary mode"
        )

    roots: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        try:
            root = Path(value).expanduser().resolve()
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"invalid work root {value!r}: {exc}") from exc
        if root not in seen:
            roots.append(root)
            seen.add(root)
    return roots