"""Task types for the FUSION point-cloud package."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ..core import FlowContext


@dataclass(frozen=True, slots=True, kw_only=True)
class FusionTask:
    """Pointed at a FUSION executable, optionally via Wine.

    ``fusion_dir`` defaults to the ``FUSION_DIR`` environment variable so a suite
    can pin the install location once rather than repeating it on every task.
    """

    name: str
    executable: str
    fusion_dir: str | None = None
    args: Mapping[str, Any] = field(default_factory=dict)
    use_wine: bool = False

    @property
    def executable_path(self) -> str:
        """Resolve the executable relative to the configured FUSION directory."""

        return str(PurePosixPath(self._resolved_dir()) / self.executable)

    def _resolved_dir(self) -> str:
        """Return the per-task dir, falling back to the ``FUSION_DIR`` env var."""

        return self.fusion_dir or os.environ.get("FUSION_DIR", "")

    def to_command(self, context: FlowContext) -> tuple[list[str], str | None]:
        """Render to an argv, building the stage config for the target executable."""

        cfg = context.resolve(self.args)
        if not isinstance(cfg, Mapping):
            raise TypeError("resolved fusion args must be a mapping")
        config_cls = _fusion_config_for(self.executable)
        task = config_cls(**cfg)
        argv = [self.executable_path, *task.to_argv()]
        if self.use_wine:
            argv = ["wine", *argv]
        return argv, None


@dataclass(frozen=True, slots=True)
class CanopyModelTask:
    """Fusionic configuration for CanopyModel."""

    surfacefile: str | Path
    cellsize: float
    xyunits: str
    zunits: str
    coordsys: int
    zone: int
    horizdatum: int
    vertdatum: int
    datafiles: tuple[str | Path, ...] = ()
    median: int | None = None
    smooth: int | None = None
    texture: int | None = None
    slope: bool = False
    aspect: bool = False
    outlier: tuple[float, float] | None = None
    multiplier: float | None = None
    return_spec: str | None = None
    class_spec: str | None = None
    ignoreoverlap: bool = False
    hole: float | None = None
    ascii: bool = False
    surface: bool = False
    peaks: bool = False
    pointcount: bool = False
    nofill: bool = False
    grid: tuple[float, float, float, float] | None = None
    gridxy: tuple[float, float, float, float] | None = None
    align: str | Path | None = None
    extent: str | Path | None = None
    rasterorigin: bool = False
    ground: str | Path | None = None

    def to_args(self) -> dict[str, object]:
        args: dict[str, object] = {
            "surfacefile": str(self.surfacefile),
            "cellsize": self.cellsize,
            "xyunits": self.xyunits,
            "zunits": self.zunits,
            "coordsys": self.coordsys,
            "zone": self.zone,
            "horizdatum": self.horizdatum,
            "vertdatum": self.vertdatum,
            "datafiles": [str(path) for path in self.datafiles],
        }
        _maybe_set(args, "median", self.median)
        _maybe_set(args, "smooth", self.smooth)
        _maybe_set(args, "texture", self.texture)
        _maybe_set(args, "slope", self.slope, false_value=False)
        _maybe_set(args, "aspect", self.aspect, false_value=False)
        _maybe_set(args, "outlier", self.outlier)
        _maybe_set(args, "multiplier", self.multiplier)
        _maybe_set(args, "return", self.return_spec)
        _maybe_set(args, "class", self.class_spec)
        _maybe_set(args, "ignoreoverlap", self.ignoreoverlap, false_value=False)
        _maybe_set(args, "hole", self.hole)
        _maybe_set(args, "ascii", self.ascii, false_value=False)
        _maybe_set(args, "surface", self.surface, false_value=False)
        _maybe_set(args, "peaks", self.peaks, false_value=False)
        _maybe_set(args, "pointcount", self.pointcount, false_value=False)
        _maybe_set(args, "nofill", self.nofill, false_value=False)
        _maybe_set(args, "grid", self.grid)
        _maybe_set(args, "gridxy", self.gridxy)
        _maybe_set(args, "align", str(self.align) if self.align is not None else None)
        _maybe_set(args, "extent", str(self.extent) if self.extent is not None else None)
        _maybe_set(args, "rasterorigin", self.rasterorigin, false_value=False)
        _maybe_set(args, "ground", str(self.ground) if self.ground is not None else None)
        return {key: value for key, value in args.items() if value is not None and value != []}

    def to_argv(self) -> list[str]:
        argv = [
            str(self.surfacefile),
            str(self.cellsize),
            _unit(self.xyunits),
            _unit(self.zunits),
            str(self.coordsys),
            str(self.zone),
            str(self.horizdatum),
            str(self.vertdatum),
        ]
        if self.ground is not None:
            argv.insert(0, f"/ground:{self.ground}")
        if self.median is not None:
            argv.insert(0, f"/median:{self.median}")
        if self.smooth is not None:
            argv.insert(0, f"/smooth:{self.smooth}")
        if self.texture is not None:
            argv.insert(0, f"/texture:{self.texture}")
        if self.slope:
            argv.insert(0, "/slope")
        if self.aspect:
            argv.insert(0, "/aspect")
        if self.outlier is not None:
            argv.insert(0, f"/outlier:{self.outlier[0]},{self.outlier[1]}")
        if self.multiplier is not None:
            argv.insert(0, f"/multiplier:{self.multiplier}")
        if self.return_spec is not None:
            argv.insert(0, f"/return:{self.return_spec}")
        if self.class_spec is not None:
            argv.insert(0, f"/class:{self.class_spec}")
        if self.ignoreoverlap:
            argv.insert(0, "/ignoreoverlap")
        if self.hole is not None:
            argv.insert(0, f"/hole:{self.hole}")
        if self.ascii:
            argv.insert(0, "/ascii")
        if self.surface:
            argv.insert(0, "/surface")
        if self.peaks:
            argv.insert(0, "/peaks")
        if self.pointcount:
            argv.insert(0, "/pointcount")
        if self.nofill:
            argv.insert(0, "/nofill")
        if self.grid is not None:
            argv.insert(0, f"/grid:{_csv(self.grid)}")
        if self.gridxy is not None:
            argv.insert(0, f"/gridxy:{_csv(self.gridxy)}")
        if self.align is not None:
            argv.insert(0, f"/align:{self.align}")
        if self.extent is not None:
            argv.insert(0, f"/extent:{self.extent}")
        if self.rasterorigin:
            argv.insert(0, "/rasterorigin")
        return argv + [str(path) for path in self.datafiles]


@dataclass(frozen=True, slots=True)
class GroundFilterTask:
    """Fusionic configuration for GroundFilter (bare-earth classification)."""

    outputfile: str | Path
    cellsize: float
    datafiles: tuple[str | Path, ...]
    gparam: float | None = None
    wparam: float | None = None
    iterations: int | None = None
    window: float | None = None
    slope: float | None = None
    threshold: float | None = None

    def to_args(self) -> dict[str, object]:
        args: dict[str, object] = {
            "outputfile": str(self.outputfile),
            "cellsize": self.cellsize,
            "datafiles": [str(path) for path in self.datafiles],
        }
        _maybe_set(args, "gparam", self.gparam)
        _maybe_set(args, "wparam", self.wparam)
        _maybe_set(args, "iterations", self.iterations)
        _maybe_set(args, "window", self.window)
        _maybe_set(args, "slope", self.slope)
        _maybe_set(args, "threshold", self.threshold)
        return args

    def to_argv(self) -> list[str]:
        argv: list[str] = []
        if self.gparam is not None:
            argv.append(f"/gparam:{self.gparam}")
        if self.wparam is not None:
            argv.append(f"/wparam:{self.wparam}")
        if self.iterations is not None:
            argv.append(f"/iterations:{self.iterations}")
        if self.window is not None:
            argv.append(f"/window:{self.window}")
        if self.slope is not None:
            argv.append(f"/slope:{self.slope}")
        if self.threshold is not None:
            argv.append(f"/threshold:{self.threshold}")
        argv += [str(self.outputfile), str(self.cellsize)]
        argv += [str(path) for path in self.datafiles]
        return argv


@dataclass(frozen=True, slots=True)
class GridSurfaceCreateTask:
    """Fusionic configuration for GridSurfaceCreate (gridded surface model)."""

    surfacefile: str | Path
    cellsize: float
    xyunits: str
    zunits: str
    coordsys: int
    zone: int
    horizdatum: int
    vertdatum: int
    datafiles: tuple[str | Path, ...]
    median: int | None = None
    smooth: int | None = None
    peaks: bool = False
    nodata: float | None = None

    def to_args(self) -> dict[str, object]:
        args: dict[str, object] = {
            "surfacefile": str(self.surfacefile),
            "cellsize": self.cellsize,
            "xyunits": self.xyunits,
            "zunits": self.zunits,
            "coordsys": self.coordsys,
            "zone": self.zone,
            "horizdatum": self.horizdatum,
            "vertdatum": self.vertdatum,
            "datafiles": [str(path) for path in self.datafiles],
        }
        _maybe_set(args, "median", self.median)
        _maybe_set(args, "smooth", self.smooth)
        _maybe_set(args, "peaks", self.peaks, false_value=False)
        _maybe_set(args, "nodata", self.nodata)
        return args

    def to_argv(self) -> list[str]:
        argv: list[str] = []
        if self.median is not None:
            argv.append(f"/median:{self.median}")
        if self.smooth is not None:
            argv.append(f"/smooth:{self.smooth}")
        if self.peaks:
            argv.append("/peaks")
        if self.nodata is not None:
            argv.append(f"/nodata:{self.nodata}")
        argv += [
            str(self.surfacefile),
            str(self.cellsize),
            _unit(self.xyunits),
            _unit(self.zunits),
            str(self.coordsys),
            str(self.zone),
            str(self.horizdatum),
            str(self.vertdatum),
        ]
        argv += [str(path) for path in self.datafiles]
        return argv


@dataclass(frozen=True, slots=True)
class DTM2TIFTask:
    """Fusionic configuration for DTM2TIF (PLANS DTM to grayscale TIFF)."""

    inputfile: str | Path
    outputfile: str | Path | None = None
    mask: bool = False

    def to_args(self) -> dict[str, object]:
        args: dict[str, object] = {
            "inputfile": str(self.inputfile),
        }
        if self.outputfile is not None:
            args["outputfile"] = str(self.outputfile)
        _maybe_set(args, "mask", self.mask, false_value=False)
        return args

    def to_argv(self) -> list[str]:
        argv: list[str] = []
        if self.mask:
            argv.append("/mask")
        argv.append(str(self.inputfile))
        if self.outputfile is not None:
            argv.append(str(self.outputfile))
        return argv


_FUSION_TOOLS: dict[str, type] = {
    "canopymodel.exe": CanopyModelTask,
    "canopymodel64.exe": CanopyModelTask,
    "groundfilter.exe": GroundFilterTask,
    "groundfilter64.exe": GroundFilterTask,
    "gridsurfacecreate.exe": GridSurfaceCreateTask,
    "gridsurfacecreate64.exe": GridSurfaceCreateTask,
    "dtm2tif.exe": DTM2TIFTask,
    "dtm2tif64.exe": DTM2TIFTask,
}


def _fusion_config_for(executable: str) -> type:
    try:
        return _FUSION_TOOLS[executable.lower()]
    except KeyError:
        raise ValueError(f"no FUSION config registered for executable: {executable}") from None


def _maybe_set(target: dict[str, object], key: str, value: object, *, false_value: object | None = None) -> None:
    if value is None:
        return
    if value is False and false_value is None:
        return
    target[key] = value if value is not False else false_value


def _csv(values: tuple[float, float, float, float]) -> str:
    return ",".join(str(item) for item in values)


def _unit(value: str) -> str:
    return value.lower()
