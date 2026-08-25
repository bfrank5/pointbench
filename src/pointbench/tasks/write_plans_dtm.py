"""Reusable task for writing FUSION DTM files."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isnan
from pathlib import Path
from typing import Any
import struct


Number = int | float
MatrixLike = Sequence[Sequence[Number | None]]
RasterSource = str | Path
SourceLike = MatrixLike | RasterSource


@dataclass(frozen=True, slots=True)
class DTMMetadata:
    """Minimal projection metadata embedded in a DTM header."""

    xyunits: str = "M"
    zunits: str = "M"
    coordsys: int = 0
    zone: int = 0
    horizdatum: int = 0
    vertdatum: int = 0


@dataclass(frozen=True, slots=True)
class _Grid:
    rows: list[list[float]]
    origin_x: float
    origin_y: float
    column_spacing: float
    row_spacing: float


def write_plans_dtm(
    source: SourceLike,
    file_name: str | Path,
    *,
    description: str = "DTM written by pointbench",
    origin_x: float | None = None,
    origin_y: float | None = None,
    column_spacing: float | None = None,
    row_spacing: float | None = None,
    rotate: bool = True,
    storage_format: int = -1,
    metadata: DTMMetadata | None = None,
    tile_size: int | None = None,
) -> bool:
    """Write a FUSION DTM file from a matrix or raster source.

    Raster inputs use rasterio for grid extraction and metadata inference.
    When tile_size is provided for raster input, data are streamed tile-by-tile
    directly into the output DTM.
    """

    if storage_format < -1 or storage_format > 3:
        raise ValueError("storage_format must be -1, 0, 1, 2, or 3")

    raster_tile_size = tile_size if isinstance(source, (str, Path)) else None
    if raster_tile_size is not None and raster_tile_size <= 0:
        raise ValueError("tile_size must be positive")

    if raster_tile_size is not None:
        return _write_raster_tiled_dtm(
            Path(source),
            file_name,
            description=description,
            storage_format=storage_format,
            metadata=metadata,
            tile_size=raster_tile_size,
        )

    grid = _load_grid(source, origin_x, origin_y, column_spacing, row_spacing)
    rows = grid.rows
    row_count = len(rows)
    column_count = len(rows[0])

    values: list[float] = []
    min_z = None
    max_z = None
    vals_int = True
    for row in rows:
        for value in row:
            if value is None or (isinstance(value, float) and isnan(value)):
                value = -1
            if not isinstance(value, int):
                vals_int = False
            numeric = float(value)
            values.append(numeric)
            min_z = numeric if min_z is None or numeric < min_z else min_z
            max_z = numeric if max_z is None or numeric > max_z else max_z

    write_rows = rows
    if rotate:
        write_rows = [list(reversed(col)) for col in zip(*rows, strict=True)]

    meta = metadata or DTMMetadata()
    xyunits_int = _units_code(meta.xyunits)
    zunits_int = _units_code(meta.zunits)
    storage_code = 0 if vals_int else 2 if storage_format == -1 else storage_format

    path = Path(file_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as con:
        header = bytearray(82)
        signature = b"PLANS-PC BINARY .DTM"
        header[: len(signature)] = signature
        desc = description[:60].encode("ascii", "replace")
        header[len(signature) : len(signature) + len(desc)] = desc
        con.write(header)
        con.write(struct.pack("<f", 3.1))
        con.write(struct.pack("<d", grid.origin_x))
        con.write(struct.pack("<d", grid.origin_y))
        con.write(struct.pack("<d", float(min_z)))
        con.write(struct.pack("<d", float(max_z)))
        con.write(struct.pack("<d", 0.0))
        con.write(struct.pack("<d", grid.column_spacing))
        con.write(struct.pack("<d", grid.row_spacing))
        con.write(struct.pack("<i", column_count))
        con.write(struct.pack("<i", row_count))
        con.write(struct.pack("<h", xyunits_int))
        con.write(struct.pack("<h", zunits_int))
        con.write(struct.pack("<h", storage_code))
        con.write(struct.pack("<h", meta.coordsys))
        con.write(struct.pack("<h", meta.zone))
        con.write(struct.pack("<h", meta.horizdatum))
        con.write(struct.pack("<h", meta.vertdatum))
        con.seek(200)

        flat = [_sanitize_value(value) for row in write_rows for value in row]
        _write_flat_values(con, flat, storage_format, vals_int)

    return True


def _load_grid(
    source: SourceLike,
    origin_x: float | None,
    origin_y: float | None,
    column_spacing: float | None,
    row_spacing: float | None,
) -> _Grid:
    if isinstance(source, (str, Path)):
        return _load_raster(Path(source))
    if origin_x is None or origin_y is None or column_spacing is None or row_spacing is None:
        raise ValueError("matrix inputs require origin_x, origin_y, column_spacing, and row_spacing")
    rows = _coerce_matrix(source)
    return _Grid(rows=rows, origin_x=origin_x, origin_y=origin_y, column_spacing=column_spacing, row_spacing=row_spacing)


def _load_raster(path: Path) -> _Grid:
    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover - dependency detection
        raise RuntimeError("raster inputs require rasterio") from exc

    with rasterio.open(path) as dataset:
        array = dataset.read(1)
        transform = dataset.transform
        origin_x = float(transform.c)
        origin_y = float(transform.f + (dataset.height * transform.e))
        column_spacing = float(transform.a)
        row_spacing = float(abs(transform.e))
        rows = _coerce_matrix(array.tolist())
    return _Grid(rows=rows, origin_x=origin_x, origin_y=origin_y, column_spacing=column_spacing, row_spacing=row_spacing)


def _load_raster_tiled(path: Path, tile_size: int) -> _Grid:
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:  # pragma: no cover - dependency detection
        raise RuntimeError("raster inputs require rasterio") from exc

    with rasterio.open(path) as dataset:
        transform = dataset.transform
        origin_x = float(transform.c)
        origin_y = float(transform.f + (dataset.height * transform.e))
        column_spacing = float(transform.a)
        row_spacing = float(abs(transform.e))
        rows: list[list[float | int | None]] = []
        for row_off in range(0, dataset.height, tile_size):
            row_rows: list[list[float | int | None]] = []
            window_height = min(tile_size, dataset.height - row_off)
            for col_off in range(0, dataset.width, tile_size):
                window_width = min(tile_size, dataset.width - col_off)
                window = Window(col_off, row_off, window_width, window_height)
                chunk = dataset.read(1, window=window, masked=True)
                chunk_rows = chunk.filled(-1).tolist()
                if not row_rows:
                    row_rows = [list(row) for row in chunk_rows]
                else:
                    for idx, chunk_row in enumerate(chunk_rows):
                        row_rows[idx].extend(chunk_row)
            rows.extend(row_rows)
    return _Grid(rows=rows, origin_x=origin_x, origin_y=origin_y, column_spacing=column_spacing, row_spacing=row_spacing)


def _write_raster_tiled_dtm(
    path: Path,
    file_name: str | Path,
    *,
    description: str,
    storage_format: int,
    metadata: DTMMetadata | None,
    tile_size: int,
    min_z: float = 0.0,
    max_z: float = 10000.0,
    assume_float: bool = True,
) -> bool:
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:  # pragma: no cover - dependency detection
        raise RuntimeError("raster inputs require rasterio") from exc

    with rasterio.open(path) as dataset:
        transform = dataset.transform
        origin_x = float(transform.c)
        origin_y = float(transform.f + (dataset.height * transform.e))
        column_spacing = float(transform.a)
        row_spacing = float(abs(transform.e))

        vals_int = not assume_float and storage_format == -1 and _dataset_is_int(dataset, tile_size)
        storage_code = 0 if vals_int else 2 if storage_format == -1 else storage_format

        meta = metadata or DTMMetadata()
        xyunits_int = _units_code(meta.xyunits)
        zunits_int = _units_code(meta.zunits)

        out = Path(file_name)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as con:
            _write_header(
                con,
                description=description,
                origin_x=origin_x,
                origin_y=origin_y,
                min_z=min_z,
                max_z=max_z,
                column_spacing=column_spacing,
                row_spacing=row_spacing,
                column_count=dataset.width,
                row_count=dataset.height,
                xyunits_int=xyunits_int,
                zunits_int=zunits_int,
                storage_code=storage_code,
                metadata=meta,
            )

            for row_off in range(0, dataset.height, tile_size):
                window_height = min(tile_size, dataset.height - row_off)
                for col_off in range(0, dataset.width, tile_size):
                    window_width = min(tile_size, dataset.width - col_off)
                    window = Window(col_off, row_off, window_width, window_height)
                    chunk = dataset.read(1, window=window, masked=True)
                    _write_chunk(con, chunk.filled(-1), storage_format, vals_int)

    return True


def _write_header(
    con: Any,
    *,
    description: str,
    origin_x: float,
    origin_y: float,
    min_z: float,
    max_z: float,
    column_spacing: float,
    row_spacing: float,
    column_count: int,
    row_count: int,
    xyunits_int: int,
    zunits_int: int,
    storage_code: int,
    metadata: DTMMetadata,
) -> None:
    header = bytearray(82)
    signature = b"PLANS-PC BINARY .DTM"
    header[: len(signature)] = signature
    desc = description[:60].encode("ascii", "replace")
    header[len(signature) : len(signature) + len(desc)] = desc
    con.write(header)
    con.write(struct.pack("<f", 3.1))
    con.write(struct.pack("<d", origin_x))
    con.write(struct.pack("<d", origin_y))
    con.write(struct.pack("<d", min_z))
    con.write(struct.pack("<d", max_z))
    con.write(struct.pack("<d", 0.0))
    con.write(struct.pack("<d", column_spacing))
    con.write(struct.pack("<d", row_spacing))
    con.write(struct.pack("<i", column_count))
    con.write(struct.pack("<i", row_count))
    con.write(struct.pack("<h", xyunits_int))
    con.write(struct.pack("<h", zunits_int))
    con.write(struct.pack("<h", storage_code))
    con.write(struct.pack("<h", metadata.coordsys))
    con.write(struct.pack("<h", metadata.zone))
    con.write(struct.pack("<h", metadata.horizdatum))
    con.write(struct.pack("<h", metadata.vertdatum))
    con.seek(200)


def _write_chunk(con: Any, chunk: Any, storage_format: int, vals_int: bool) -> None:
    flat = [_sanitize_value(value) for row in chunk.tolist() for value in row]
    _write_flat_values(con, flat, storage_format, vals_int)


def _write_flat_values(con: Any, flat: list[float], storage_format: int, vals_int: bool) -> None:
    if storage_format == -1:
        if vals_int:
            con.write(struct.pack(f"<{len(flat)}h", *(_coerce_int(v) for v in flat)))
        else:
            con.write(struct.pack(f"<{len(flat)}f", *flat))
    elif storage_format == 0:
        con.write(struct.pack(f"<{len(flat)}h", *(_coerce_int(v) for v in flat)))
    elif storage_format == 1:
        con.write(struct.pack(f"<{len(flat)}i", *(_coerce_int(v) for v in flat)))
    elif storage_format == 2:
        con.write(struct.pack(f"<{len(flat)}f", *flat))
    else:
        con.write(struct.pack(f"<{len(flat)}d", *flat))


def _window_is_int(chunk: Any) -> bool:
    for row in chunk.tolist():
        for value in row:
            if value is None:
                continue
            if isinstance(value, float) and value.is_integer():
                continue
            if isinstance(value, int):
                continue
            return False
    return True


def _chunk_min_max(chunk: Any) -> tuple[float, float]:
    values: list[float] = []
    for row in chunk.tolist():
        for value in row:
            values.append(_sanitize_value(value))
    return min(values), max(values)


def _coerce_matrix(source: Sequence[Sequence[Any]]) -> list[list[float | int | None]]:
    rows = [list(row) for row in source]
    if not rows or not rows[0]:
        raise ValueError("source must contain at least one row and column")
    columns = len(rows[0])
    for row in rows:
        if len(row) != columns:
            raise ValueError("source must be rectangular")
    return rows


def _sanitize_value(value: Any) -> float:
    if value is None or (isinstance(value, float) and isnan(value)):
        return -1.0
    return float(value)


def _coerce_int(value: float) -> int:
    return int(value)


def _units_code(value: str) -> int:
    code = value.upper()
    if code == "F":
        return 0
    if code == "O":
        return 3
    return 1
