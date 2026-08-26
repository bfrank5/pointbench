from pathlib import Path

from pointbench import FlowContext, LasRTask, LidRTask


def test_lasr_task_to_command_renders_pipeline():
    task = LasRTask(name="dtm", source="${inputs.lidar}", output="${outputs.dtm}", resolution=1.0)
    context = FlowContext(inputs={"lidar": "in.las"}, outputs={"dtm": "out.tif"})

    argv, stdin = task.to_command(context)

    assert argv[1] == "--vanilla"
    script = Path(argv[2]).read_text(encoding="utf-8")
    assert "library(lasR)" in script
    assert "classify_with_ptd()" in script
    assert "rasterize(1.0,'mean',filter='Classification == 2'" in script
    assert 'ofile="out.tif"' in script
    assert '"in.las"' in script
    assert stdin is None


def test_lidr_task_to_command_renders_pipeline():
    task = LidRTask(name="dtm", source="${inputs.lidar}", output="${outputs.dtm}", resolution=1.0)
    context = FlowContext(inputs={"lidar": "in.las"}, outputs={"dtm": "out.tif"})

    argv, stdin = task.to_command(context)

    assert argv[1] == "--vanilla"
    script = Path(argv[2]).read_text(encoding="utf-8")
    assert "library(lidR)" in script
    assert "classify_ground(las, ptd())" in script
    assert "rasterize(v, r, field='Z', fun='mean')" in script
    assert 'writeRaster(dtm, "out.tif"' in script
    assert stdin is None
