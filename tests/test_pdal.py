import json
from subprocess import CompletedProcess

import pointbench.runner as runner_mod
from pointbench import (
    FlowContext,
    FlowInput,
    FlowOutput,
    FlowSpec,
    PDALStage,
    PDALTask,
    run_flow,
    write_run_result_json,
)


def test_pdal_stage_to_json():
    stage = PDALStage(type="readers.las", options={"filename": "tile.laz"})

    assert stage.to_json() == {"type": "readers.las", "filename": "tile.laz"}


def test_pdal_task_to_command_serializes_pipeline():
    task = PDALTask(
        name="normalize",
        pipeline=(
            PDALStage(type="readers.las", options={"filename": "tile.laz"}),
            PDALStage(type="filters.outlier", options={"method": "statistical", "mean_k": 8}),
            PDALStage(type="writers.gdal", options={"filename": "out.tif"}),
        ),
    )

    argv, stdin = task.to_command(FlowContext())

    assert argv == ["pdal", "pipeline", "--stdin"]
    assert json.loads(stdin) == [
        {"type": "readers.las", "filename": "tile.laz"},
        {"type": "filters.outlier", "method": "statistical", "mean_k": 8},
        {"type": "writers.gdal", "filename": "out.tif"},
    ]


def test_pdal_task_resolves_context_refs_in_stage_options():
    task = PDALTask(
        name="chm",
        pipeline=(PDALStage(type="readers.las", options={"filename": "${inputs.lidar}"}),),
    )
    context = FlowContext(inputs={"lidar": "data/tile.laz"})

    _, stdin = task.to_command(context)

    assert json.loads(stdin) == [{"type": "readers.las", "filename": "data/tile.laz"}]


def test_pdal_task_allows_executable_override():
    task = PDALTask(name="clip", pipeline=(), executable="/opt/pdal/bin/pdal")

    argv, _ = task.to_command(FlowContext())

    assert argv == ["/opt/pdal/bin/pdal", "pipeline", "--stdin"]


def test_pdal_task_uses_pdal_executable_env_default(monkeypatch):
    monkeypatch.setenv("PDAL_EXECUTABLE", "/env/pdal")
    task = PDALTask(name="clip", pipeline=())

    argv, _ = task.to_command(FlowContext())

    assert argv == ["/env/pdal", "pipeline", "--stdin"]


def test_pdal_task_per_task_executable_beats_env(monkeypatch):
    monkeypatch.setenv("PDAL_EXECUTABLE", "/env/pdal")
    task = PDALTask(name="clip", pipeline=(), executable="/pinned/pdal")

    argv, _ = task.to_command(FlowContext())

    assert argv == ["/pinned/pdal", "pipeline", "--stdin"]


def test_pdal_task_falls_back_to_path_default(monkeypatch):
    monkeypatch.delenv("PDAL_EXECUTABLE", raising=False)
    task = PDALTask(name="clip", pipeline=())

    argv, _ = task.to_command(FlowContext())

    assert argv == ["pdal", "pipeline", "--stdin"]


def test_run_flow_dispatches_pdal_task_via_to_command(monkeypatch):
    spec = FlowSpec(
        name="pdal-demo",
        inputs=(FlowInput(name="lidar", path="data/tile.laz"),),
        tasks=(
            PDALTask(
                name="outlier",
                pipeline=(PDALStage(type="readers.las", options={"filename": "${inputs.lidar}"}),),
            ),
        ),
        outputs=(FlowOutput(name="out", path="out.laz"),),
    )
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["stdin"] = kwargs.get("input")
        return CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(runner_mod, "run", fake_run)

    result = run_flow(spec, verbose=False)

    assert captured["argv"] == ["pdal", "pipeline", "--stdin"]
    assert json.loads(captured["stdin"]) == [{"type": "readers.las", "filename": "data/tile.laz"}]
    assert result.results[0].task_name == "outlier"


def test_write_run_result_json_handles_external_task_outcome(tmp_path, monkeypatch):
    spec = FlowSpec(
        name="pdal-demo",
        inputs=(FlowInput(name="lidar", path="data/tile.laz"),),
        tasks=(
            PDALTask(
                name="outlier",
                pipeline=(PDALStage(type="readers.las", options={"filename": "${inputs.lidar}"}),),
            ),
        ),
        outputs=(FlowOutput(name="dtm", path="out.tif"),),
    )

    def fake_run(argv, **kwargs):
        return CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(runner_mod, "run", fake_run)

    result = run_flow(spec, verbose=False)
    path = write_run_result_json(result, tmp_path / "run.json")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["tasks"][0]["name"] == "outlier"
    assert payload["outputs"]["dtm"] == "out.tif"
    assert payload["outputs"]["outlier"]["returncode"] == 0
    assert payload["outputs"]["outlier"]["stdout"] == "{}"
