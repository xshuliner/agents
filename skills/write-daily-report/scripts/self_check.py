#!/usr/bin/env python3
"""Check that this transferable skill is runnable on the current machine."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from platform_paths import app_homes


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    checks = {
        "python": {"ok": sys.version_info >= (3, 9), "version": sys.version.split()[0]},
        "git": {"ok": shutil.which("git") is not None},
        "skill": {"ok": (ROOT / "SKILL.md").is_file()},
        "collectors": {"ok": all((ROOT / "scripts" / name).is_file() for name in (
            "collect_codex_sessions.py", "collect_claude_sessions.py", "collect_cursor_sessions.py",
            "collect_pi_sessions.py", "collect_qoder_sessions.py", "collect_teleagent_sessions.py",
            "collect_trae_sessions.py",
        ))},
        "dataHomes": {
            name: [str(path) for path in app_homes(env, name)]
            for env, name in (("CURSOR_HOME", "Cursor"), ("TRAE_HOME", "Trae"), ("QODER_HOME", "Qoder"))
        },
    }
    checks["ok"] = all(item["ok"] for key, item in checks.items() if key not in {"dataHomes", "ok"})
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
