"""Task type for the lasR point-cloud package."""

from __future__ import annotations

from dataclasses import dataclass

from ..core import FlowContext
from .r import resolve_rscript, r_path, write_temp_script


@dataclass(frozen=True, slots=True, kw_only=True)
class LasRTask:
    """Run a lasR DTM pipeline (ground filter + rasterize) via Rscript.

    Emits a single inline ``exec(...)`` pipeline (the form lasR handles
    reliably) and runs it with ``Rscript --vanilla`` to avoid locale-related
    instability on R >= 4.5 Windows.
    """

    name: str
    source: str
    output: str
    resolution: float = 1.0
    rscript: str | None = None

    def to_command(self, context: FlowContext) -> tuple[list[str], str | None]:
        src = context.resolve(self.source)
        out = context.resolve(self.output)
        code = _dtm_script(src, out, self.resolution)
        script = write_temp_script(code)
        return [resolve_rscript(self.rscript), "--vanilla", str(script)], None


def _dtm_script(source: str, output: str, resolution: float) -> str:
    return (
        "suppressMessages(library(lasR))\n"
        f"exec(reader_las()+classify_with_ptd()+"
        f"rasterize({resolution!r},'mean',filter='Classification == 2',"
        f"ofile={r_path(output)}), {r_path(source)})\n"
    )
