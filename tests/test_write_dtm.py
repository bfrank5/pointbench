from pathlib import Path
import importlib.util
import struct

from pointbench import DTMMetadata, write_plans_dtm


def test_write_dtm_writes_expected_header_and_payload(tmp_path: Path):
    out = tmp_path / "sample.dtm"

    assert write_plans_dtm(
        [[1, 2], [3, None]],
        out,
        origin_x=10.0,
        origin_y=20.0,
        column_spacing=1.5,
        row_spacing=2.5,
        metadata=DTMMetadata(xyunits="M", zunits="M", coordsys=1, zone=2, horizdatum=3, vertdatum=4),
    ) is True

    data = out.read_bytes()
    assert data.startswith(b"PLANS-PC BINARY .DTM")

    version = struct.unpack_from("<f", data, 82)[0]
    origin_x = struct.unpack_from("<d", data, 86)[0]
    origin_y = struct.unpack_from("<d", data, 94)[0]
    min_z = struct.unpack_from("<d", data, 102)[0]
    max_z = struct.unpack_from("<d", data, 110)[0]
    columns = struct.unpack_from("<i", data, 142)[0]
    rows = struct.unpack_from("<i", data, 146)[0]

    assert version == 3.1
    assert origin_x == 10.0
    assert origin_y == 20.0
    assert min_z == -1.0
    assert max_z == 3.0
    assert columns == 2
    assert rows == 2


def test_write_dtm_from_raster(tmp_path: Path):
    if importlib.util.find_spec("rasterio") is None or importlib.util.find_spec("numpy") is None:
        return

    import numpy as np
    import rasterio

    src = tmp_path / "sample.tif"
    out = tmp_path / "sample.dtm"

    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    with rasterio.open(
        src,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=data.dtype,
        crs="EPSG:32610",
        transform=rasterio.transform.from_origin(100.0, 200.0, 5.0, 7.5),
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)

    assert write_plans_dtm(src, out) is True

    payload = out.read_bytes()
    assert struct.unpack_from("<d", payload, 86)[0] == 100.0
    assert struct.unpack_from("<d", payload, 94)[0] == 185.0
    assert struct.unpack_from("<d", payload, 118)[0] == 0.0
    assert struct.unpack_from("<d", payload, 126)[0] == 5.0
    assert struct.unpack_from("<d", payload, 134)[0] == 7.5
    assert struct.unpack_from("<i", payload, 142)[0] == 2
    assert struct.unpack_from("<i", payload, 146)[0] == 2


def test_write_dtm_rejects_ragged_matrix(tmp_path: Path):
    try:
        write_plans_dtm([[1, 2], [3]], tmp_path / "bad.dtm", origin_x=0, origin_y=0, column_spacing=1, row_spacing=1)
    except ValueError as exc:
        assert str(exc) == "source must be rectangular"
    else:
        raise AssertionError("expected ValueError")
