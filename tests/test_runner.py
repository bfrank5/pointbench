from pathlib import Path

from pointbench import FlowInput, FlowOutput, FlowSpec, FlowTask, run_flow


def test_run_flow_binds_declared_outputs(tmp_path: Path):
    out = tmp_path / "sample.dtm"
    spec = FlowSpec(
        name="demo",
        inputs=(FlowInput(name="dtm_source", path=str(tmp_path / "source.tif")),),
        tasks=(
            FlowTask(
                name="make_dtm",
                command="pointbench.tasks.write_plans_dtm:write_plans_dtm",
                args={
                    "source": [[1, 2], [3, None]],
                    "file_name": str(out),
                    "origin_x": 10.0,
                    "origin_y": 20.0,
                    "column_spacing": 1.5,
                    "row_spacing": 2.5,
                },
            ),
            FlowTask(
                name="check_dtm",
                command="pointbench.tasks.file_ops:file_exists",
                args={"path": "${outputs.canopy_height_model}"},
            ),
        ),
        outputs=(FlowOutput(name="canopy_height_model", path=str(out)),),
    )

    result = run_flow(spec)

    assert result.context.outputs["canopy_height_model"] == str(out)
    assert result.context.tasks["make_dtm"] is True
    assert result.context.tasks["check_dtm"] is True
    assert result.results[0].task_name == "make_dtm"
    assert result.results[1].task_name == "check_dtm"
