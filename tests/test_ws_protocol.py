"""The protocol freeze, which a study's stamp and `ws check` share."""

import datetime
from pathlib import Path

import pytest
import yaml
from ws import protocol

PLAN = """# Plan

## Protocol

Shared: burst pressure, three liners.
<!-- a note to self -->

### 02-burst

Mesh h = 1 mm.

### 03-fatigue

Ten cycles.

## Deviations

| Date | Phase | Deviation | Decided | Why |
|---|---|---|---|---|
"""


def phase(tmp_path: Path, plan: str = PLAN) -> Path:
    folder = tmp_path / "phases" / "02-burst"
    folder.mkdir(parents=True)
    (folder / "config.yaml").write_text("# The burst phase\ntype: confirm\n")
    (tmp_path / "PLAN.md").write_text(plan)
    return folder


def test_a_phase_protocol_is_the_shared_text_and_its_own_subsection() -> None:
    text = protocol.protocol(PLAN, "02-burst")

    assert "Shared: burst pressure" in text and "Mesh h = 1 mm." in text
    assert "Ten cycles" not in text and "note to self" not in text


def test_comments_and_trailing_spaces_do_not_change_the_hash() -> None:
    edited = PLAN.replace("a note to self", "another note").replace("1 mm.", "1 mm.   ")

    assert protocol.digest(edited, "02-burst") == protocol.digest(PLAN, "02-burst")
    assert protocol.digest(PLAN.replace("1 mm", "2 mm"), "02-burst") != protocol.digest(
        PLAN, "02-burst"
    )


def test_freeze_records_the_hash_and_keeps_the_configuration(tmp_path: Path) -> None:
    folder = phase(tmp_path)

    protocol.freeze(folder, tmp_path / "PLAN.md", datetime.date(2026, 10, 1))

    text = (folder / "config.yaml").read_text()
    assert text.startswith("# The burst phase\ntype: confirm\n")
    record = yaml.safe_load(text)["protocol"]
    assert record == {"hash": protocol.digest(PLAN, "02-burst"), "frozen": "2026-10-01"}
    protocol.check(folder, tmp_path / "PLAN.md")


def test_refreezing_a_changed_protocol_needs_a_logged_deviation(tmp_path: Path) -> None:
    folder = phase(tmp_path)
    plan = tmp_path / "PLAN.md"
    protocol.freeze(folder, plan, datetime.date(2026, 10, 1))
    plan.write_text(PLAN.replace("1 mm", "0.5 mm"))

    with pytest.raises(protocol.ProtocolError, match="log the change as a deviation"):
        protocol.freeze(folder, plan, datetime.date(2026, 10, 5))
    with pytest.raises(protocol.ProtocolError, match="changed since it was frozen"):
        protocol.check(folder, plan)

    plan.write_text(
        plan.read_text() + "| 2026-10-04 | 02-burst | finer mesh | before | GCI too wide |\n"
    )
    protocol.freeze(folder, plan, datetime.date(2026, 10, 5))

    record = yaml.safe_load((folder / "config.yaml").read_text())["protocol"]
    assert record["frozen"] == "2026-10-05"
    assert record["previous"] == [
        {"hash": protocol.digest(PLAN, "02-burst"), "frozen": "2026-10-01"}
    ]
    protocol.check(folder, plan)


def test_nothing_to_freeze_is_refused(tmp_path: Path) -> None:
    folder = phase(tmp_path, "# Plan\n\n## Protocol\n\n<!-- to do -->\n")

    with pytest.raises(protocol.ProtocolError, match="no protocol"):
        protocol.freeze(folder, tmp_path / "PLAN.md")
