import pytest

from pointbench import DTM2TIFTask, FlowContext, FusionTask, GridSurfaceCreateTask, GroundFilterTask


def test_ground_filter_task_to_argv():
    task = GroundFilterTask(
        outputfile="out.las",
        cellsize=5,
        datafiles=("in.las",),
        iterations=8,
    )

    assert task.to_argv() == ["/iterations:8", "out.las", "5", "in.las"]


def test_grid_surface_create_task_to_argv():
    task = GridSurfaceCreateTask(
        surfacefile="out.dtm",
        cellsize=1,
        xyunits="m",
        zunits="m",
        coordsys=1,
        zone=10,
        horizdatum=2,
        vertdatum=2,
        datafiles=("ground.las",),
        median=3,
    )

    assert task.to_argv() == ["/median:3", "out.dtm", "1", "m", "m", "1", "10", "2", "2", "ground.las"]


def test_dtm2tif_task_to_argv():
    task = DTM2TIFTask(inputfile="in.dtm", outputfile="out.tif")

    assert task.to_argv() == ["in.dtm", "out.tif"]


def test_dtm2tif_task_defaults_output_and_mask():
    task = DTM2TIFTask(inputfile="in.dtm", mask=True)

    assert task.to_argv() == ["/mask", "in.dtm"]


def test_fusion_task_dispatches_dtm2tif_config():
    task = FusionTask(
        name="conv",
        executable="DTM2TIF64.exe",
        fusion_dir="/f",
        args={"inputfile": "${outputs.dtm}", "outputfile": "${outputs.tif}"},
    )
    context = FlowContext(outputs={"dtm": "in.dtm", "tif": "out.tif"})

    argv, _ = task.to_command(context)

    assert argv == ["/f/DTM2TIF64.exe", "in.dtm", "out.tif"]


def test_fusion_task_dispatches_config_by_executable():
    task = FusionTask(
        name="ground",
        executable="groundfilter64.exe",
        fusion_dir="/f",
        args={"outputfile": "${outputs.ground_pts}", "cellsize": 5.0, "datafiles": ["${inputs.lidar}"]},
    )
    context = FlowContext(inputs={"lidar": "in.las"}, outputs={"ground_pts": "out.las"})

    argv, stdin = task.to_command(context)

    assert argv == ["/f/groundfilter64.exe", "out.las", "5.0", "in.las"]
    assert stdin is None


def test_fusion_task_uses_fusion_dir_env_fallback(monkeypatch):
    monkeypatch.setenv("FUSION_DIR", "/env/fusion")
    task = FusionTask(name="ground", executable="groundfilter.exe", args={})

    assert task.executable_path == "/env/fusion/groundfilter.exe"


def test_fusion_task_unknown_executable_raises():
    task = FusionTask(name="x", executable="UnknownTool.exe", fusion_dir="/f", args={})

    with pytest.raises(ValueError):
        task.to_command(FlowContext())
