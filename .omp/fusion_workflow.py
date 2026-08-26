"""FUSION workflow scratchpad: derive a ground DTM from a lidar tile.

Implements the canonical FUSION DTM recipe from the manual:
    GroundFilter      -> isolate bare-earth points
    GridSurfaceCreate -> rasterize ground points to a PLANS .dtm surface

Both are pointbench :class:`FusionTask` steps, dispatched by executable name
to their FUSION configs. The install location is resolved from ``.omp/.env``
(``FUSION_DIR``) so tasks don't repeat it.

Run with:
    python .omp/fusion_workflow.py
"""

import os
from pathlib import Path

from pointbench import (
    FlowTask,
    FlowInput,
    FlowOutput,
    FlowSpec,
    FusionTask,
    run_flow,
    write_run_result_json,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _load_env() -> None:
    """Apply .omp/.env so the suite resolves the right FUSION directory."""

    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env()

input_las = DATA / "autzen_trim.las"
ground_las = DATA / "autzen_fusion_ground.las"
dtm_path = DATA / "autzen_fusion.dtm"
tif_path = DATA / "autzen_fusion.tif"
results_json = DATA / "autzen_fusion_run.json"

ground_task = FusionTask(
    name="ground_filter",
    executable="groundfilter64.exe",
    args={
        "outputfile": "${outputs.ground_pts}",
        "cellsize": 5.0,
        "datafiles": ["${inputs.lidar}"],
    },
)

dtm_task = FusionTask(
    name="surface_create",
    executable="GridSurfaceCreate64.exe",
    args={
        "surfacefile": "${outputs.dtm}",
        "cellsize": 1.0,
        "xyunits": "m",
        "zunits": "m",
        "coordsys": 1,
        "zone": 10,
        "horizdatum": 2,
        "vertdatum": 2,
        "datafiles": ["${outputs.ground_pts}"],
    },
)

convert_task = FlowTask(
    name="dtm_to_geotiff",
    command="pointbench.tasks.dtm_to_geotiff:dtm_to_geotiff",
    args={
        "source": "${outputs.dtm}",
        "file_name": "${outputs.tif}",
        "crs": "EPSG:2994",
    },
)

flow = FlowSpec(
    name="autzen-dtm-fusion",
    description="Derive a ground DTM from the Autzen lidar tile with FUSION.",
    inputs=(FlowInput(name="lidar", path=str(input_las)),),
    tasks=(ground_task, dtm_task, convert_task),
    outputs=(
        FlowOutput(name="ground_pts", path=str(ground_las)),
        FlowOutput(name="dtm", path=str(dtm_path)),
        FlowOutput(name="tif", path=str(tif_path)),
    ),
)

# Aliases for an interactive session.
spec = flow


def main() -> None:
    result = run_flow(flow)
    path = write_run_result_json(result, results_json)
    print(f"Ground points written to: {ground_las}")
    print(f"DTM written to: {dtm_path}")
    print(f"TIFF written to: {tif_path}")
    print(f"Results written to: {path}")


if __name__ == "__main__":
    main()
