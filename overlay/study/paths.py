"""Where the study keeps what git does not."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# One folder per phase, one per run inside it: RUNS / "03-mixed-formulation" / <run>.
# In the study by default, out of git; {{runs_env}} moves them (to another drive).
RUNS = Path(os.environ.get("{{runs_env}}") or ROOT / "runs").expanduser()
