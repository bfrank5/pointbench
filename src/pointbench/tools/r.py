"""Shared helpers for R-backed point-cloud tasks (lidR, lasR)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

RSCRIPT_ENV = "RSCRIPT"


def resolve_rscript(override: str | None) -> str:
    """Resolve the Rscript executable: per-task pin, then env, then PATH."""

    return override or os.environ.get(RSCRIPT_ENV) or "Rscript"


def write_temp_script(code: str) -> Path:
    """Write R source to a temp file and return its path."""

    fd, path = tempfile.mkstemp(suffix=".R", prefix="pointbench_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(code)
    return Path(path)


def r_path(path: str | Path) -> str:
    """Quote a filesystem path as an R string literal (forward slashes)."""

    return '"' + str(path).replace("\\", "/").replace('"', '\\"') + '"'
