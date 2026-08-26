`pointbench` is a benchmarking system for large scale point cloud processing,
typically as it manifests in the remote sensing of forested environments.

Point cloud processing is a creative enterprise, often involving multiple pieces
of software required to make desired outputs. `pointbench` tackles this by
defining flows, which are a series of steps needed to produce a particular
output. Users define flows in Python, constructing them from the `pointbench`
API to outline the inputs, processing steps, and outputs for a given flow.
`pointbench` executes the flow, logging the processing time and memory
consumption of each step.

As an example, a flow defining the computation of a canopy height model in
FUSION might look like

```python
from pointbench import FlowInput, FlowOutput, FlowSpec, FusionTask

flow = FlowSpec(
    name="canopy-height-model-fusion",
    description="Derive a canopy height model from a raw lidar tile.",
    inputs=(
        FlowInput(name="lidar_tiles", path="./data/my_lidar_tile.laz"),
    ),
    tasks=(
        FusionTask(
            name="normalize",
            fusion_dir="/path/to/FUSION",
            executable="ClipData.exe",
            args={
                "input": "${inputs.lidar_tiles}",
                "output": "build/normalized.laz",
            },
        ),
        FusionTask(
            name="generate_chm",
            fusion_dir="/path/to/FUSION",
            executable="CanopyModel.exe",
            args={
                "input": "build/normalized.laz",
                "output": "build/canopy_height_model.tif",
            },
        ),
    ),
    outputs=(
        FlowOutput(name="canopy_height_model", path="build/canopy_height_model.tif"),
    ),
)
```
