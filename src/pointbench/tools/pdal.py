"""Task types for the PDAL point-cloud package."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core import FlowContext


@dataclass(frozen=True, slots=True, kw_only=True)
class PDALStage:
    """A single PDAL pipeline stage (reader, filter, or writer)."""

    type: str
    options: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Serialize to a PDAL pipeline stage object."""

        return {"type": self.type, **self.options}


@dataclass(frozen=True, slots=True, kw_only=True)
class PDALTask:
    """One PDAL pipeline, executed as a single subprocess.

    Stages are serialized to a PDAL pipeline JSON payload and piped to
    ``pdal pipeline --stdin``, so the whole reader/filter/writer chain streams
    through one process.
    """

    name: str
    pipeline: tuple[PDALStage, ...]
    executable: str | None = None

    def to_json(self, context: FlowContext) -> list[dict[str, Any]]:
        """Serialize the pipeline to PDAL JSON, resolving ``${...}`` refs."""

        return [{"type": stage.type, **context.resolve(stage.options)} for stage in self.pipeline]

    def to_command(self, context: FlowContext) -> tuple[list[str], str | None]:
        """Render to an argv with the pipeline JSON as stdin."""

        payload = json.dumps(self.to_json(context))
        return [self._resolve_executable(), "pipeline", "--stdin"], payload

    def _resolve_executable(self) -> str:
        """Resolve the pdal binary: per-task pin, then env, then PATH default."""

        return self.executable or os.environ.get("PDAL_EXECUTABLE") or "pdal"
