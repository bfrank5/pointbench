"""Core typed model for pointbench flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowInput:
    """Named external input to a flow."""

    name: str
    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowTask:
    """Executable step within a flow (in-process Python function)."""

    name: str
    command: str
    args: Mapping[str, Any] = field(default_factory=dict)


class ExternalTask(Protocol):
    """Capability shared by subprocess-backed tasks (FUSION, PDAL, ...).

    Implementations render themselves into an ``argv`` plus an optional stdin
    payload, which the runner executes and times as one subprocess.
    """

    name: str

    def to_command(self, context: "FlowContext") -> tuple[list[str], str | None]: ...


@dataclass(slots=True)
class FlowContext:
    """Resolved flow state shared across tasks."""

    flow_name: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    tasks: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    def resolve(self, value: Any) -> Any:
        """Substitute ``${...}`` references against this context, recursively."""

        if isinstance(value, str):
            return _resolve_string(value, self)
        if isinstance(value, Mapping):
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.resolve(item) for item in value)
        return value


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
    tasks: tuple[FlowTask | ExternalTask, ...] = ()
    outputs: tuple[FlowOutput, ...] = ()


def _resolve_string(value: str, context: FlowContext) -> Any:
    if not (value.startswith("${") and value.endswith("}")):
        return value
    path = value[2:-1].strip()
    parts = path.split(".") if path else []
    current: Any = context
    for part in parts:
        if isinstance(current, FlowContext):
            current = getattr(current, part)
        elif isinstance(current, Mapping):
            current = current[part]
        else:
            current = getattr(current, part)
    return current


def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
