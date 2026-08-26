"""Benchmark chart: bar chart of per-tool DTM pipeline wall time.

Runs each tool's DTM flow and plots total elapsed time as bars. A tool that
fails to run (e.g. lidR, environmentally blocked under R 4.5.0 on this machine)
is drawn in red and labeled "blocked" rather than crashing the chart.

Run with:
    python .omp/benchmark_chart.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt

from pointbench import run_flow

import fusion_workflow
import lasr_workflow
import lidr_workflow
import pdal_workflow

TOOLS = [
    ("PDAL", pdal_workflow.flow, Path("data/autzen_dtm.tif")),
    ("FUSION", fusion_workflow.flow, Path("data/autzen_fusion.tif")),
    ("lasR", lasr_workflow.flow, Path("data/autzen_lasr.tif")),
    ("lidR", lidr_workflow.flow, Path("data/autzen_lidr.tif")),
]

labels: list[str] = []
times: list[float] = []
blocked: list[bool] = []

for name, flow, output in TOOLS:
    try:
        result = run_flow(flow, verbose=False)
        total = sum(task.elapsed_s for task in result.results)
        produced = output.exists()
        labels.append(name)
        times.append(total)
        blocked.append(not produced)
        print(f"{name}: {total:.2f}s{' (no output)' if not produced else ''}")
    except Exception as exc:  # noqa: BLE001 - a failing tool must not sink the chart
        labels.append(name)
        times.append(0.0)
        blocked.append(True)
        print(f"{name}: BLOCKED ({exc.__class__.__name__})")

fig, ax = plt.subplots(figsize=(7, 5))
colors = ["#c0392b" if b else "#2980b9" for b in blocked]
ax.bar(labels, times, color=colors)
ax.set_ylabel("elapsed time (s)")
ax.set_title("Autzen DTM pipeline wall time by tool")
for i, (t, b) in enumerate(zip(times, blocked)):
    ax.text(i, t, "blocked" if b else f"{t:.2f}s", ha="center", va="bottom", fontsize=9)
fig.tight_layout()

out = Path(__file__).resolve().parents[1] / "data" / "benchmark_dtm_times.png"
fig.savefig(out, dpi=150)
print(f"saved {out}")
