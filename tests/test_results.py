import json
from pathlib import Path

from pointbench import FlowContext, FlowRunResult, TaskResult, write_run_result_json


def test_write_run_result_json(tmp_path: Path):
    result = FlowRunResult(
        results=(TaskResult(task_name="a", elapsed_s=1.25), TaskResult(task_name="b", elapsed_s=2.5)),
        context=FlowContext(inputs={"raw": "input.tif"}, outputs={"canopy_height_model": "out.dtm"}),
    )

    path = write_run_result_json(result, tmp_path / "run.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["tasks"][0]["name"] == "a"
    assert payload["tasks"][1]["elapsed_s"] == 2.5
    assert payload["inputs"]["raw"] == "input.tif"
    assert payload["outputs"]["canopy_height_model"] == "out.dtm"
