"""Flow execution helpers for pointbench."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from subprocess import CompletedProcess, run
from time import perf_counter
from typing import Any, Mapping

from .core import FlowContext, FlowOutput, FlowSpec, FlowTask, TaskResult


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
    task: FlowTask | object,
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
        outcome = _run_external_task(task, context=context, base_dir=base_dir)
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


def _run_external_task(task: object, *, context: FlowContext, base_dir: str | Path | None) -> CompletedProcess[str]:
    argv, stdin = task.to_command(context)
    cwd = Path(base_dir) if base_dir is not None else None
    # check=False: a non-zero exit is recorded in the task outcome rather than
    # aborting the whole flow, so a failing step still yields its timing/result.
    return run(argv, input=stdin, check=False, text=True, capture_output=True, cwd=cwd)


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
    elif isinstance(outcome, CompletedProcess):
        context.outputs[task_name] = {
            "returncode": outcome.returncode,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
        }
    elif outcome is not None:
        context.outputs[task_name] = outcome
