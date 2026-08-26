"""Convert a FUSION PLANS DTM file to a real-elevation GeoTIFF."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

NODATA = -9999.0

# PLANS DTM storage codes: 0=int16, 1=int32, 2=float32, 3=float64.
_DTYPE: dict[int, str] = {0: "<i2", 1: "<i4", 2: "<f4", 3: "<f8"}


def dtm_to_geotiff(
    source: str | Path,
    file_name: str | Path,
    *,
    crs: Any,
    nodata: float = NODATA,
) -> bool:
    """Write a real-elevation GeoTIFF from a FUSION PLANS DTM grid.

    Reads the float elevation grid, origin, and spacing from the PLANS header and
    writes a rasterio GeoTIFF carrying the supplied CRS. FUSION's own ``DTM2TIF``
    produces a grayscale render (elevations scaled to 1-255) with no projection,
    which is not a usable DTM; this reads the underlying float surface instead.

    PLANS stores rows top-to-north with ``origin_y`` at the south edge, so the
    top-left transform origin is ``origin_y + row_count * row_spacing``.
    """

    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    source_path = Path(source)
    with source_path.open("rb") as con:
        header = con.read(200)

    origin_x = struct.unpack_from("<d", header, 86)[0]
    origin_y = struct.unpack_from("<d", header, 94)[0]
    column_spacing = struct.unpack_from("<d", header, 126)[0]
    row_spacing = struct.unpack_from("<d", header, 134)[0]
    column_count = struct.unpack_from("<i", header, 142)[0]
    row_count = struct.unpack_from("<i", header, 146)[0]
    storage_code = struct.unpack_from("<h", header, 154)[0]

    dtype = _DTYPE.get(storage_code)
    if dtype is None:
        raise ValueError(f"unsupported DTM storage code: {storage_code}")

    count = column_count * row_count
    with source_path.open("rb") as con:
        con.seek(200)
        raw = con.read(count * np.dtype(dtype).itemsize)
    values = np.frombuffer(raw, dtype=dtype).reshape(row_count, column_count)
    values = values.astype("float32")
    # FUSION writes -1.0 for empty cells; mask only that sentinel so genuine
    # below-sea-level elevations are not erased as nodata.
    values[values <= -1.0] = nodata

    transform = from_origin(
        origin_x,
        origin_y + row_count * row_spacing,
        column_spacing,
        row_spacing,
    )

    out = Path(file_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out,
        "w",
        driver="GTiff",
        height=row_count,
        width=column_count,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(values, 1)
    return True
