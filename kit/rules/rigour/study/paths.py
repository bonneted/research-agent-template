"""Where the inquiry keeps what git does not."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# One folder per phase, one per run inside it: RUNS / "03-mixed-formulation" / <run>.
# In the inquiry by default, out of git; RKT_RUNS moves them (to another drive).
RUNS = Path(os.environ.get("RKT_RUNS") or ROOT / "runs").expanduser()
