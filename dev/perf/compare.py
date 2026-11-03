# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Compares a run of dev/perf/record.sh with the baseline; exits 1 if any measure is worse than allowed

Usage: python dev/perf/compare.py dev/perf/baselines <run-dir>

A measure is worse than allowed when it is more than ALLOWED_WORSENING worse and more than its
noise floor worse, except HTTP calls, of which one more is a regression. Compare only runs made
on the same machine.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List

ALLOWED_WORSENING = 0.10
# unit: (noise floor, whether a larger value is worse)
UNITS = {
    "ms": (5.0, True),
    "roundtrip_ms": (100.0, True),
    "bytes": (1024.0, True),
    "MiB": (5.0, True),
    "cpu_s": (1.0, True),
    "jobs/min": (1.0, False),
    "calls": (0.0, True),
}


@dataclass(frozen=True)
class Measure:
    name: str
    unit: str
    value: float


def main(baseline_dir: Path, run_dir: Path) -> int:
    """Prints each measure beside its baseline, and returns 1 if any is worse than allowed"""
    baseline = {m.name: m for m in read_measures(baseline_dir)}
    run = {m.name: m for m in read_measures(run_dir)}
    regressions = []
    for name, measure in sorted(run.items()):
        before = baseline.get(name)
        if before is None:
            print(f"  new   {name}: {measure.value:.2f} {measure.unit}")
            continue
        is_regression = is_worse_than_allowed(before, measure)
        flag = "WORSE" if is_regression else "ok"
        print(
            f"  {flag:5} {name}: {before.value:.2f} -> {measure.value:.2f} {measure.unit}"
        )
        if is_regression:
            regressions.append(name)

    if regressions:
        print(
            f"{len(regressions)} measures worse than allowed: {', '.join(regressions)}"
        )
        return 1
    return 0


def read_measures(folder: Path) -> List[Measure]:
    """Reads the measures of the client benchmarks and the round trip in the folder"""
    return [
        *_read_client(folder / "client.json"),
        *_read_roundtrip(folder / "roundtrip.json"),
    ]


def is_worse_than_allowed(before: Measure, after: Measure) -> bool:
    """Whether the measure got worse by more than ALLOWED_WORSENING and its noise floor"""
    noise_floor, is_larger_worse = UNITS[after.unit]
    worsening = (
        after.value - before.value if is_larger_worse else before.value - after.value
    )
    if after.unit == "calls":
        return worsening > 0
    return worsening > noise_floor and worsening > ALLOWED_WORSENING * abs(before.value)


def _read_client(path: Path) -> Iterator[Measure]:
    if not path.exists():
        return
    for benchmark in json.loads(path.read_text())["benchmarks"]:
        name = f"client.{benchmark['name']}"
        extra: Dict[str, float] = benchmark["extra_info"]
        yield Measure(f"{name}.median", "ms", benchmark["stats"]["median"] * 1000)
        if "http_calls" in extra:
            yield Measure(f"{name}.http_calls", "calls", extra["http_calls"])
        if "peak_memory_bytes" in extra:
            yield Measure(
                f"{name}.peak_memory", "MiB", extra["peak_memory_bytes"] / 1024**2
            )
        if "upload_bytes" in extra:
            yield Measure(f"{name}.upload", "bytes", extra["upload_bytes"])


def _read_roundtrip(path: Path) -> Iterator[Measure]:
    if not path.exists():
        return
    data = json.loads(path.read_text())
    for kind, stats in data["kinds"].items():
        name = f"roundtrip.{kind}"
        yield Measure(f"{name}.p50", "roundtrip_ms", stats["p50_ms"])
        yield Measure(f"{name}.p95", "roundtrip_ms", stats["p95_ms"])
        yield Measure(f"{name}.throughput", "jobs/min", stats["jobs_per_minute"])
        yield Measure(f"{name}.http_calls", "calls", stats["http_calls_per_job"])
        yield Measure(f"{name}.upload", "bytes", stats["upload_bytes_per_job"])
    for process, stats in data["processes"].items():
        yield Measure(f"process.{process}.peak_rss", "MiB", stats["peak_rss_mib"])
        yield Measure(f"process.{process}.cpu", "cpu_s", stats["cpu_seconds"])


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
