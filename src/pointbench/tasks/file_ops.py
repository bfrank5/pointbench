"""Small reusable file-oriented tasks."""

from __future__ import annotations

from pathlib import Path


def file_exists(path: str | Path) -> bool:
    return Path(path).exists()
