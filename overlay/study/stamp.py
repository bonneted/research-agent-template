"""The run stamp: what it takes to reproduce a run, written into its folder (rule 7).

A phase's `run.py` wraps its work in `run`:

    with stamp.run(Path(__file__).parent, seed) as folder:
        ...  # write results into `folder`

The stamp records the study commit and whether the tree was clean (the diff is saved
beside it when not), the library's install as `spimat.installed_from()` reports it, the
phase's configuration, the seed, the hardware and the wall-clock. A runner that builds
each run's configuration (a base file plus overrides) passes it as `config`: the stamp
records it as `run_config`, beside the phase's. A run in a confirm phase refuses to
start on a dirty tree.
"""

import copy
import json
import os
import platform
import shutil
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import yaml

from study.paths import ROOT, RUNS

STAMP = "stamp.json"
DIFF = "diff.patch"
CONFIG = "config.yaml"


class DirtyTree(RuntimeError):
    """A confirm run was asked for on a study tree with uncommitted changes."""


def _git(*args: str, root: Path, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=check, capture_output=True, text=True
    ).stdout


def _diff(root: Path) -> bytes:
    """The uncommitted changes, untracked files included, without touching the index.

    Bytes: a binary patch, or a file in another encoding, is saved as git writes it.
    """
    command = ["git", "diff", "--binary"]
    diff = subprocess.run([*command, "HEAD"], cwd=root, check=True, capture_output=True).stdout
    for name in _git("ls-files", "--others", "--exclude-standard", "-z", root=root).split("\0"):
        if not name:
            continue
        untracked = subprocess.run(
            [*command, "--no-index", "--", os.devnull, name], cwd=root, capture_output=True
        )
        # Exits 1 when the files differ, which they always do here; more is an error.
        if untracked.returncode > 1:
            raise subprocess.CalledProcessError(untracked.returncode, untracked.args, stderr=untracked.stderr)
        diff += untracked.stdout
    return diff


def _library() -> dict:
    """The library's install; for an editable one, the commit and state of its checkout."""
    # Imported here, so the study's tests can stand a fake spimat in before the import.
    import spimat

    report = spimat.installed_from()
    path = report.get("path")
    if report.get("editable") and path and (Path(path) / ".git").exists():
        checkout = Path(path)
        report = {
            **report,
            "commit": _git("rev-parse", "HEAD", root=checkout).strip(),
            "dirty": bool(_git("status", "--porcelain", root=checkout).strip()),
        }
    return report


def _hardware() -> dict:
    hardware = {
        "host": platform.node(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpus": os.cpu_count(),
        "python": platform.python_version(),
    }
    try:
        import jax
    except ImportError:
        return hardware
    hardware["jax"] = jax.__version__
    hardware["devices"] = [str(device) for device in jax.devices()]
    return hardware


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def run(
    phase: Path,
    seed: int,
    *,
    name: str | None = None,
    config: dict | None = None,
    root: Path = ROOT,
    runs: Path = RUNS,
) -> Iterator[Path]:
    """Stamp a run of `phase` (its folder) in a new folder `runs/<phase>/<name>`, and yield it.

    `name` defaults to the start time and the seed. `config`, the run's resolved
    configuration, is recorded as `run_config` beside the phase's. The stamp gets its
    wall-clock and end time when the block ends, even by an exception (then `failed` is
    true).
    Raises `DirtyTree` for a confirm phase whose study has uncommitted changes, and
    `ValueError` for a phase whose `config.yaml` declares no type.
    """
    phase = Path(phase).resolve()
    text = (phase / CONFIG).read_text(encoding="utf-8")
    phase_config = yaml.safe_load(text) or {}
    kind = phase_config.get("type")
    if kind not in ("explore", "confirm"):
        raise ValueError(f"{phase / CONFIG}: declare the phase `type: explore` or `type: confirm`")
    dirty = bool(_git("status", "--porcelain", root=root).strip())
    if dirty and kind == "confirm":
        raise DirtyTree(
            f"confirm phase {phase.name}: the study has uncommitted changes; "
            "commit them (or stash them) before a confirm run, so it stamps a commit alone"
        )
    started = _now()
    stamp_time = datetime.fromisoformat(started).strftime("%Y%m%dT%H%M%S")
    folder = Path(runs) / phase.name / (name or f"{stamp_time}-seed{seed}")
    folder.mkdir(parents=True)
    if dirty:
        (folder / DIFF).write_bytes(_diff(root))
    shutil.copyfile(phase / CONFIG, folder / CONFIG)
    record = {
        "study": {"commit": _git("rev-parse", "HEAD", root=root).strip(), "dirty": dirty},
        "library": _library(),
        "phase": {"name": phase.name, "type": kind},
        "config": phase_config,
        **({"run_config": copy.deepcopy(config)} if config is not None else {}),
        "seed": seed,
        "hardware": _hardware(),
        "started": started,
    }

    def write(**end: object) -> None:
        (folder / STAMP).write_text(json.dumps({**record, **end}, indent=2) + "\n", encoding="utf-8")

    write()
    clock = time.perf_counter()
    failed = True
    try:
        yield folder
        failed = False
    finally:
        write(finished=_now(), wall_clock_s=time.perf_counter() - clock, failed=failed)
