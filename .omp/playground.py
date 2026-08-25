"""Scratchpad for experimenting with pointbench's Python API.

Run with:
    python .omp/playground.py
    python -i .omp/playground.py
"""

from pathlib import Path

from pointbench import (
    CanopyModelTask,
    FlowInput,
    FlowOutput,
    FlowSpec,
    FlowTask,
    FusionTask,
    TaskResult,
    run_flow,
    write_run_result_json,
)

fusion_dir = "/home/bryce/.wine/drive_c/Program Files/FUSION"
build_dir = "/media/bryce/BigDrive/pb"
json_path = Path(build_dir) / "run.json"

dtm_task = FlowTask(
    name="tif_to_plans_dtm",
    command="pointbench.tasks.write_plans_dtm:write_plans_dtm",
    args={
        "source": "/media/bryce/BigDrive/beachie/BeachieCreekLionshead_DTM.tif",
        "file_name": f"{build_dir}/beachie_dtm.dtm",
        "tile_size": 512,
    },
)

canopy_cfg = CanopyModelTask(
    surfacefile=f"{build_dir}/canopy_height_model.dtm",
    cellsize=5,
    xyunits="m",
    zunits="m",
    coordsys=1,
    zone=10,
    horizdatum=2,
    vertdatum=2,
    datafiles=("${inputs.dap_tile}",),
    ground="${outputs.beachie_dtm}",
    median=3,
    smooth=5,
    peaks=True,
)

canopy_task = FusionTask(
    name="make_canopy_model",
    fusion_dir=fusion_dir,
    executable="CanopyModel.exe",
    use_wine=True,
    args=canopy_cfg.to_args(),
)

flow = FlowSpec(
    name="canopy-height-model-fusion",
    description="Derive a canopy height model from a raw DAP tile.",
    inputs=(
        FlowInput(name="dap_tile", path="/media/bryce/BigDrive/beachie_dap/PointCloud_02757.laz"),
        FlowInput(name="dtm", path="/media/bryce/BigDrive/beachie/BeachieCreekLionshead_DTM.tif"),
    ),
    tasks=(
        dtm_task,
        canopy_task,
    ),
    outputs=(
        FlowOutput(name="beachie_dtm", path=f"{build_dir}/beachie_dtm.dtm"),
        FlowOutput(name="canopy_height_model", path=f"{build_dir}/canopy_height_model.dtm"),
    ),
)

# Handy aliases to poke at in an interactive session.
spec = flow
input0 = spec.inputs[0]
task0 = spec.tasks[0]
task1 = spec.tasks[1]
output0 = spec.outputs[0]
result0 = TaskResult(task_name=task0.name, elapsed_s=12.34)
result1 = TaskResult(task_name=task1.name, elapsed_s=45.67)


def show() -> FlowSpec:
    """Return the sample spec for quick inspection in a REPL."""

    return spec


def main() -> None:
    """Run the sample flow and persist a JSON summary."""

    result = run_flow(flow)
    path = write_run_result_json(result, json_path)
    print(path)


if __name__ == "__main__":
    main()
