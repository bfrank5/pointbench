from pointbench import FlowInput, FlowOutput, FlowSpec, FlowTask, FusionTask, TaskResult, greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_name():
    assert greet("Bryce") == "Hello, Bryce!"


def test_task_result_records_elapsed_time():
    result = TaskResult(task_name="normalize", elapsed_s=1.25)

    assert result.task_name == "normalize"
    assert result.elapsed_s == 1.25


def test_fusion_task_defaults_to_no_wine():
    task = FusionTask(
        name="clip",
        fusion_dir="/home/bryce/.wine/drive_c/Program Files/FUSION",
        executable="ClipData.exe",
        args={"input": "in.laz", "output": "out.laz"},
    )

    assert task.executable_path == "/home/bryce/.wine/drive_c/Program Files/FUSION/ClipData.exe"
    assert task.use_wine is False


def test_fusion_task_can_use_wine():
    task = FusionTask(
        name="clip",
        fusion_dir="/home/bryce/.wine/drive_c/Program Files/FUSION",
        executable="ClipData.exe",
        args={},
        use_wine=True,
    )

    assert task.use_wine is True
    assert task.executable_path.endswith("/Program Files/FUSION/ClipData.exe")


def test_flow_spec_from_mapping():
    spec = FlowSpec.from_mapping(
        {
            "name": "canopy-height-model-fusion",
            "description": "Derive a canopy height model from a raw lidar tile.",
            "inputs": [{"name": "lidar_tiles", "path": "./data/my_lidar_tile.laz"}],
            "tasks": [
                {
                    "kind": "fusion",
                    "name": "normalize",
                    "fusion_dir": "/home/bryce/.wine/drive_c/Program Files/FUSION",
                    "executable": "ClipData.exe",
                    "use_wine": True,
                    "args": {"input": "${inputs.lidar_tiles}", "output": "build/normalized.laz"},
                }
            ],
            "outputs": [{"name": "canopy_height_model", "path": "build/canopy_height_model.tif"}],
        }
    )

    assert spec == FlowSpec(
        name="canopy-height-model-fusion",
        description="Derive a canopy height model from a raw lidar tile.",
        inputs=(FlowInput(name="lidar_tiles", path="./data/my_lidar_tile.laz"),),
        tasks=(
            FusionTask(
                name="normalize",
                fusion_dir="/home/bryce/.wine/drive_c/Program Files/FUSION",
                executable="ClipData.exe",
                args={"input": "${inputs.lidar_tiles}", "output": "build/normalized.laz"},
                use_wine=True,
            ),
        ),
        outputs=(FlowOutput(name="canopy_height_model", path="build/canopy_height_model.tif"),),
    )


def test_flow_spec_rejects_missing_name():
    try:
        FlowSpec.from_mapping({})
    except ValueError as exc:
        assert str(exc) == "name must be a non-empty string"
    else:
        raise AssertionError("expected ValueError")
