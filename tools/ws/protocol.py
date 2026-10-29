"""The protocol freeze: a confirm phase's protocol is fixed in `PLAN.md` before its first
run, and its hash recorded in the phase's `config.yaml` (core rule 1).

A phase's protocol is the `## Protocol` section of `PLAN.md`: its text before the first
`###` heading, which every phase shares, and the `###` subsection whose heading starts
with the phase's number or name (`### 02-burst`), if there is one. HTML comments and
trailing spaces do not count. Freezing records

    protocol:
      hash: <sha256 of the protocol>
      frozen: <date>

in `phases/NN-slug/config.yaml`. A confirm run refuses to start when the protocol's hash
is not the frozen one. A protocol changed after its freeze is refrozen only once a
deviation for the phase, dated on or after the freeze, is in `PLAN.md`; the earlier
freezes are kept under `previous`.

`ws` spawns each study with a copy of this file as `study/protocol.py`, and its stamp
uses it; in a study, freeze with `uv run python -m study.protocol freeze phases/NN-slug`.
The standard library and PyYAML only.
"""

import datetime
import hashlib
import re
import sys
from pathlib import Path

import yaml

PLAN = "PLAN.md"
CONFIG = "config.yaml"
KEY = "protocol"
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class ProtocolError(ValueError):
    """The protocol cannot be frozen, or a confirm run does not match its freeze."""


def _section(text: str, heading: str) -> list[str]:
    """The lines of the `## heading` section of a Markdown text, without its heading."""
    lines = text.replace("\r\n", "\n").split("\n")
    starts = [index for index, line in enumerate(lines) if line.strip() == f"## {heading}"]
    if not starts:
        return []
    start = starts[0] + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start:end]


def _names(phase: str) -> set[str]:
    """What a heading or table cell may call the phase `NN-slug`: its name or number."""
    return {phase, phase.split("-")[0]}


def _first_word(text: str) -> str:
    words = text.strip().split()
    return words[0].strip(":.,") if words else ""


def protocol(plan: str, phase: str) -> str:
    """The protocol of `phase` in the text `plan`, as it is hashed."""
    lines = _section(_COMMENT.sub("", plan), "Protocol")
    shared, own, current = [], [], None
    for line in lines:
        if line.startswith("### "):
            current = _first_word(line[4:]) in _names(phase)
        target = shared if current is None else own if current else None
        if target is not None:
            target.append(line.rstrip())
    return "\n".join([*shared, *own]).strip("\n")


def digest(plan: str, phase: str) -> str:
    """The hash of the protocol of `phase`, as a freeze records it."""
    return hashlib.sha256(protocol(plan, phase).encode("utf-8")).hexdigest()


def deviations(plan: str, phase: str) -> list[str]:
    """The dates of the deviations `PLAN.md` logs for `phase`, in its Deviations table."""
    dates = []
    for line in _section(plan, "Deviations"):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not _DATE.fullmatch(cells[0]):
            continue
        if _first_word(cells[1]) in _names(phase):
            dates.append(cells[0])
    return dates


def frozen(config: dict) -> dict | None:
    """The freeze a phase's configuration records, or None."""
    record = config.get(KEY)
    return record if isinstance(record, dict) and record.get("hash") else None


def check(phase: Path, plan: Path) -> None:
    """Raise `ProtocolError` unless the phase's protocol is frozen at its current hash."""
    config = yaml.safe_load((phase / CONFIG).read_text(encoding="utf-8")) or {}
    record = frozen(config)
    if record is None:
        raise ProtocolError(
            f"confirm phase {phase.name}: its protocol is not frozen; fix it in {PLAN}, "
            f"then `uv run python -m study.protocol freeze phases/{phase.name}`"
        )
    current = digest(plan.read_text(encoding="utf-8"), phase.name)
    if current != record["hash"]:
        raise ProtocolError(
            f"confirm phase {phase.name}: the protocol in {PLAN} changed since it was "
            f"frozen on {record.get('frozen')}; log a deviation, then freeze it again"
        )


def _replace_key(text: str, block: str) -> str:
    """The YAML `text` with its top-level `protocol` key replaced by `block`, comments kept."""
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if re.match(rf"{KEY}\s*:", line)),
        None,
    )
    if start is None:
        return text + ("" if not text or text.endswith("\n") else "\n") + block
    end = start + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
        end += 1
    return "\n".join([*lines[:start], *block.rstrip("\n").split("\n"), *lines[end:]]) + "\n"


def freeze(phase: Path, plan: Path, today: datetime.date | None = None) -> str:
    """Record the hash of the phase's protocol in its `config.yaml`; returns what was done.

    Raises `ProtocolError` if the phase has no protocol, or if it was frozen at another
    hash and no deviation for it has been logged since.
    """
    today = today or datetime.date.today()
    text = plan.read_text(encoding="utf-8")
    if not protocol(text, phase.name):
        raise ProtocolError(f"{PLAN} has no protocol to freeze for {phase.name}")
    file = phase / CONFIG
    config_text = file.read_text(encoding="utf-8") if file.is_file() else ""
    config = yaml.safe_load(config_text) or {}
    current = digest(text, phase.name)
    record = frozen(config)
    if record is not None and record["hash"] == current:
        return f"{phase.name}: protocol already frozen on {record.get('frozen')}"
    previous = []
    if record is not None:
        since = str(record.get("frozen") or "")
        if not any(date >= since for date in deviations(text, phase.name)):
            raise ProtocolError(
                f"{phase.name}: the protocol changed since it was frozen on {since}; "
                f"log the change as a deviation for {phase.name} in {PLAN} first"
            )
        previous = [
            *(record.get("previous") or []),
            {"hash": record["hash"], "frozen": since},
        ]
    entry = {"hash": current, "frozen": today.isoformat()}
    if previous:
        entry["previous"] = previous
    block = yaml.safe_dump({KEY: entry}, sort_keys=False)
    file.write_text(_replace_key(config_text, block), encoding="utf-8")
    return f"{phase.name}: protocol frozen at {current[:12]}"


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "freeze":
        print("usage: python -m study.protocol freeze phases/NN-slug", file=sys.stderr)
        return 2
    phase = Path(argv[2]).resolve()
    root = phase.parents[1]
    try:
        print(freeze(phase, root / PLAN))
    except (ProtocolError, OSError) as error:
        print(f"freeze: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
