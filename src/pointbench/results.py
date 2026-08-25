"""Persistence helpers for flow run results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import FlowRunResult


def write_run_result_json(result: FlowRunResult, path: str | Path) -> Path:
    """Write a lightweight JSON summary for a completed flow run."""

    payload: dict[str, Any] = {
        "flow": {
            "name": getattr(result.context, "flow_name", None),
        },
        "tasks": [
            {"name": task.task_name, "elapsed_s": task.elapsed_s}
            for task in result.results
        ],
        "inputs": dict(result.context.inputs),
        "outputs": dict(result.context.outputs),
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
