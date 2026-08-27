"""Task type for the lidR point-cloud package."""

from __future__ import annotations

from dataclasses import dataclass

from ..core import FlowContext
from .r import resolve_rscript, r_path, write_temp_script


@dataclass(frozen=True, slots=True, kw_only=True)
class LidRTask:
    """Run a lidR DTM pipeline via Rscript.

    Uses lidR to classify ground (PTD), then rasterizes the ground points with
    ``terra`` directly rather than ``lidR::rasterize_terrain``: the latter's
    Delaunay interpolation is unreliable under R 4.5 on Windows (and crashes on
    large coordinate offsets), whereas a terra mean-per-cell surface is robust.
    Runs with ``Rscript --vanilla``.
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
        "suppressMessages(library(lidR))\n"
        "suppressMessages(library(terra))\n"
        f"las <- readLAS({r_path(source)})\n"
        "las <- classify_ground(las, ptd())\n"
        "gnd <- filter_ground(las)\n"
        "df <- as.data.frame(gnd)\n"
        "r <- rast(xmin=floor(min(df$X)), ymin=floor(min(df$Y)), "
        "xmax=ceiling(max(df$X)), ymax=ceiling(max(df$Y)), "
        f"resolution={resolution!r})\n"
        "v <- vect(df, geom=c('X','Y'))\n"
        "dtm <- rasterize(v, r, field='Z', fun='mean')\n"
        f"terra::writeRaster(dtm, {r_path(output)}, overwrite=TRUE)\n"
    )
