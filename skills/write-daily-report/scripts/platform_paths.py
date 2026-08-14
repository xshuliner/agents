#!/usr/bin/env python3
"""Platform-aware locations and URI handling for local AI clients."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def _appdata(environ: dict[str, str]) -> Path | None:
    value = environ.get("APPDATA") or environ.get("LOCALAPPDATA")
    return Path(value) if value else None


def app_homes(env_name: str, app_name: str, *, environ: dict[str, str] | None = None,
              platform: str | None = None, home: Path | None = None) -> list[Path]:
    """Return explicit override followed by conventional macOS/Windows homes."""
    environment = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    system = sys.platform if platform is None else platform
    override = environment.get(env_name)
    candidates: list[Path] = [Path(override)] if override else []
    if system.startswith("win"):
        appdata = _appdata(environment)
        if appdata:
            candidates.append(appdata / app_name)
    elif system == "darwin":
        candidates.append(user_home / "Library" / "Application Support" / app_name)
    else:
        candidates.extend((user_home / ".config" / app_name, user_home / f".{app_name.lower()}"))

    result: list[Path] = []
    for candidate in candidates:
        candidate = candidate.expanduser()
        if candidate not in result:
            result.append(candidate)
    return result


def first_app_home(env_name: str, app_name: str) -> Path:
    return app_homes(env_name, app_name)[0].resolve()


def file_uri_to_path(value: str, *, windows: bool | None = None) -> str:
    """Decode a file URI, including Windows ``file:///C:/…`` forms."""
    if not value.startswith("file://"):
        return value
    parsed = urlparse(value)
    path = unquote(parsed.path)
    use_windows = os.name == "nt" if windows is None else windows
    if use_windows:
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            return "\\\\" + parsed.netloc + path.replace("/", "\\")
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path.replace("/", "\\")
    return path
