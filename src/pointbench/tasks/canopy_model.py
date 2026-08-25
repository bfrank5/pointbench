"""Reusable task config for FUSION CanopyModel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
