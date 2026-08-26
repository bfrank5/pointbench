"""PDAL workflow scratchpad: derive a ground DTM from a lidar tile.

Uses pointbench's :class:`PDALTask` to run a PDAL reader/filter/writer chain
as a single ``pdal pipeline --stdin`` subprocess. The pdal binary is resolved
from ``.omp/.env`` (``PDAL_EXECUTABLE``) so this works without the conda env
being activated on the shell.

Run with:
    python .omp/pdal_workflow.py
"""

import os
from pathlib import Path

from pointbench import (
    FlowInput,
    FlowOutput,
    FlowSpec,
    PDALStage,
    PDALTask,
    run_flow,
    write_run_result_json,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _load_env() -> None:
    """Apply .omp/.env so the suite resolves the right pdal binary."""

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
output_tif = DATA / "autzen_dtm.tif"
results_json = DATA / "autzen_dtm_run.json"

dtm_task = PDALTask(
    name="ground_dtm",
    pipeline=(
        PDALStage(type="readers.las", options={"filename": "${inputs.lidar}"}),
        PDALStage(type="filters.elm", options={"cell": 5.0}),
        PDALStage(
            type="filters.smrf",
            options={"scalar": 1.2, "slope": 0.2, "threshold": 0.45, "window": 18.0},
        ),
        PDALStage(type="filters.range", options={"limits": "Classification[2:2]"}),
        PDALStage(
            type="writers.gdal",
            options={"filename": "${outputs.dtm}", "output_type": "idw", "resolution": 1.0},
        ),
    ),
)

flow = FlowSpec(
    name="autzen-dtm-pdal",
    description="Derive a ground DTM from the Autzen lidar tile with PDAL.",
    inputs=(FlowInput(name="lidar", path=str(input_las)),),
    tasks=(dtm_task,),
    outputs=(FlowOutput(name="dtm", path=str(output_tif)),),
)

# Aliases for an interactive session.
spec = flow


def main() -> None:
    result = run_flow(flow)
    path = write_run_result_json(result, results_json)
    print(f"DTM written to: {output_tif}")
    print(f"Results written to: {path}")


if __name__ == "__main__":
    main()
