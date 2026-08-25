"""Core typed model for pointbench flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Mapping


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowInput:
    """Named external input to a flow."""

    name: str
    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowTask:
    """Executable step within a flow."""

    name: str
    command: str
    args: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class FusionTask:
    """Pointed at a FUSION executable, optionally via Wine."""

    name: str
    fusion_dir: str
    executable: str
    args: Mapping[str, Any] = field(default_factory=dict)
    use_wine: bool = False

    @property
    def executable_path(self) -> str:
        """Resolve the executable relative to the configured FUSION directory."""

        return str(PurePosixPath(self.fusion_dir) / self.executable)


@dataclass(frozen=True, slots=True)
class FlowOutput:
    """Named flow output artifact."""

    name: str
    path: str


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Measured outcome for one executed task."""

    task_name: str
    elapsed_s: float


@dataclass(frozen=True, slots=True)
class FlowSpec:
    """Validated in-memory representation of a benchmark flow."""

    name: str
    description: str | None = None
    inputs: tuple[FlowInput, ...] = ()
    tasks: tuple[FlowTask | FusionTask, ...] = ()
    outputs: tuple[FlowOutput, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> FlowSpec:
        """Build a flow spec from a mapping loaded from YAML/JSON."""

        name = _require_str(data, "name")
        description = _optional_str(data.get("description"), "description")
        inputs = tuple(_build_inputs(data.get("inputs", ())))
        tasks = tuple(_build_tasks(data.get("tasks", ())))
        outputs = tuple(_build_outputs(data.get("outputs", ())))
        return cls(name=name, description=description, inputs=inputs, tasks=tasks, outputs=outputs)


def _require_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value


def _require_mapping(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return value


def _build_inputs(items: Any) -> list[FlowInput]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("inputs must be a list")
    inputs: list[FlowInput] = []
    for item in items:
        mapping = _require_mapping(item, "input")
        inputs.append(FlowInput(name=_require_str(mapping, "name"), path=_require_str(mapping, "path")))
    return inputs


def _build_tasks(items: Any) -> list[FlowTask | FusionTask]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("tasks must be a list")
    tasks: list[FlowTask | FusionTask] = []
    for item in items:
        mapping = _require_mapping(item, "task")
        kind = mapping.get("kind")
        if kind is None:
            tasks.append(
                FlowTask(
                    name=_require_str(mapping, "name"),
                    command=_require_str(mapping, "command"),
                    args=dict(mapping.get("args", {})),
                )
            )
            continue
        if kind != "fusion":
            raise ValueError("task kind must be 'fusion' when provided")
        tasks.append(
            FusionTask(
                name=_require_str(mapping, "name"),
                fusion_dir=_require_str(mapping, "fusion_dir"),
                executable=_require_str(mapping, "executable"),
                args=dict(mapping.get("args", {})),
                use_wine=bool(mapping.get("use_wine", False)),
            )
        )
    return tasks


def _build_outputs(items: Any) -> list[FlowOutput]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("outputs must be a list")
    outputs: list[FlowOutput] = []
    for item in items:
        mapping = _require_mapping(item, "output")
        outputs.append(FlowOutput(name=_require_str(mapping, "name"), path=_require_str(mapping, "path")))
    return outputs


def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
