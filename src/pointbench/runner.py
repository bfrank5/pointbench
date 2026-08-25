"""Flow execution helpers for pointbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from subprocess import CompletedProcess, run
from time import perf_counter
from typing import Any, Mapping

from .core import FlowOutput, FlowSpec, FlowTask, FusionTask, TaskResult
from .tasks import CanopyModelTask


@dataclass(slots=True)
class FlowContext:
    """Resolved flow state shared across tasks."""

    flow_name: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    tasks: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    def resolve(self, value: Any) -> Any:
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
class FlowRunResult:
    """Collected results from a flow execution."""

    results: tuple[TaskResult, ...]
    context: FlowContext


def run_flow(
    spec: FlowSpec,
    *,
    base_dir: str | Path | None = None,
    verbose: bool = True,
) -> FlowRunResult:
    """Execute a flow spec sequentially."""

    context = FlowContext(flow_name=spec.name, inputs={item.name: item.path for item in spec.inputs})
    _register_declared_outputs(context, spec.outputs)
    if verbose:
        print(f"[flow] {spec.name}")
    results: list[TaskResult] = []
    for task in spec.tasks:
        result = run_task(task, context=context, base_dir=base_dir, verbose=verbose)
        results.append(result)
    return FlowRunResult(results=tuple(results), context=context)


def run_task(
    task: FlowTask | FusionTask,
    *,
    context: FlowContext,
    base_dir: str | Path | None = None,
    verbose: bool = True,
) -> TaskResult:
    if verbose:
        print(f"[task] {task.name}")
    start = perf_counter()
    if isinstance(task, FlowTask):
        outcome = _run_python_task(task, context=context)
    else:
        outcome = _run_fusion_task(task, context=context, base_dir=base_dir)
    elapsed = perf_counter() - start
    context.tasks[task.name] = outcome
    _collect_outputs(task.name, outcome, context)
    if verbose:
        print(f"[done] {task.name} ({elapsed:.2f}s)")
    return TaskResult(task_name=task.name, elapsed_s=elapsed)


def _run_python_task(task: FlowTask, *, context: FlowContext) -> Any:
    module_name, func_name = _split_command(task.command)
    module = import_module(module_name)
    func = getattr(module, func_name)
    args = context.resolve(task.args)
    if not isinstance(args, Mapping):
        raise TypeError("resolved task args must be a mapping")
    return func(**args)


def _run_fusion_task(task: FusionTask, *, context: FlowContext, base_dir: str | Path | None) -> CompletedProcess[str]:
    cfg = context.resolve(task.args)
    if not isinstance(cfg, Mapping):
        raise TypeError("resolved fusion args must be a mapping")
    canopy = CanopyModelTask(**cfg)
    argv = canopy.to_argv()
    command = [task.executable_path, *argv]
    if base_dir is not None:
        cwd = Path(base_dir)
    else:
        cwd = None
    if task.use_wine:
        command = ["wine", *command]
    return run(command, check=True, text=True, capture_output=True, cwd=cwd)


def _split_command(command: str) -> tuple[str, str]:
    if ":" not in command:
        raise ValueError("command must be in 'module:function' format")
    module_name, func_name = command.split(":", 1)
    if not module_name or not func_name:
        raise ValueError("command must include both module and function")
    return module_name, func_name


def _register_declared_outputs(context: FlowContext, outputs: tuple[FlowOutput, ...]) -> None:
    for output in outputs:
        context.outputs[output.name] = output.path


def _collect_outputs(task_name: str, outcome: Any, context: FlowContext) -> None:
    if isinstance(outcome, Mapping):
        context.outputs[task_name] = dict(outcome)
        for key, value in outcome.items():
            context.outputs[key] = value
    elif outcome is not None:
        context.outputs[task_name] = outcome


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
