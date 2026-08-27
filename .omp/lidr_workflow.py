"""lidR workflow scratchpad: derive a ground DTM from a lidar tile.

Uses pointbench's :class:`LidRTask` to classify ground with lidR (PTD) and
rasterize the ground surface via terra, producing a real-elevation GeoTIFF.

NOTE: lidR's C++ paths are currently unstable under R 4.5.0 on this Windows
machine (intermittent exit-5 hard crashes). The task is correct; running it
reliably may require a healthy R/lidR install. See .omp for the lasR/FUSION/
PDAL workflows which run here.

Run with:
    python .omp/lidr_workflow.py
"""

import os
from pathlib import Path

from pointbench import FlowInput, FlowOutput, FlowSpec, LidRTask, run_flow, write_run_result_json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _load_env() -> None:
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
output_tif = DATA / "autzen_lidr.tif"
results_json = DATA / "autzen_lidr_run.json"

lidr_task = LidRTask(
    name="dtm",
    source="${inputs.lidar}",
    output="${outputs.dtm}",
    resolution=1.0,
)

flow = FlowSpec(
    name="autzen-dtm-lidr",
    description="Derive a ground DTM from the Autzen lidar tile with lidR.",
    inputs=(FlowInput(name="lidar", path=str(input_las)),),
    tasks=(lidr_task,),
    outputs=(FlowOutput(name="dtm", path=str(output_tif)),),
)

spec = flow


def main() -> None:
    result = run_flow(flow)
    path = write_run_result_json(result, results_json)
    print(f"DTM written to: {output_tif}")
    print(f"Results written to: {path}")


if __name__ == "__main__":
    main()
