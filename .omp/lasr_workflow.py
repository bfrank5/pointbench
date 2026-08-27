"""lasR workflow scratchpad: derive a ground DTM from a lidar tile.

Uses pointbench's :class:`LasRTask` to run a lasR pipeline
(PTD ground classification + mean rasterize) via Rscript, producing a
real-elevation GeoTIFF carrying the input CRS (EPSG:2994 here).

Run with:
    python .omp/lasr_workflow.py
"""

import os
from pathlib import Path

from pointbench import FlowInput, FlowOutput, FlowSpec, LasRTask, run_flow, write_run_result_json

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
output_tif = DATA / "autzen_lasr.tif"
results_json = DATA / "autzen_lasr_run.json"

lasr_task = LasRTask(
    name="dtm",
    source="${inputs.lidar}",
    output="${outputs.dtm}",
    resolution=1.0,
)

flow = FlowSpec(
    name="autzen-dtm-lasr",
    description="Derive a ground DTM from the Autzen lidar tile with lasR.",
    inputs=(FlowInput(name="lidar", path=str(input_las)),),
    tasks=(lasr_task,),
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
