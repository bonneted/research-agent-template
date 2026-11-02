"""The kit, and `rkt init`, which makes a folder an inquiry from it."""

from pathlib import Path

import yaml
from conftest import TEMPLATE
from rkt import check, inquiry, kit


def test_init_makes_an_inquiry_that_passes_its_check(tmp_path: Path) -> None:
    lines, ok = kit.init(tmp_path, "Does the sphere hold?")

    assert ok, lines
    data = yaml.safe_load((tmp_path / "inquiry.yaml").read_text())
    assert data["question"] == "Does the sphere hold?"
    assert data["kit"]["version"] == kit.version()
    assert check.check([inquiry.load(tmp_path)])[1]


def test_init_keeps_files_already_there_and_refuses_an_inquiry(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Mine\n")

    lines, ok = kit.init(tmp_path)

    assert ok
    assert f"{tmp_path}: kept AGENTS.md, already there" in lines
    assert (tmp_path / "AGENTS.md").read_text() == "# Mine\n"
    assert kit.init(tmp_path)[1] is False


def test_the_rigour_pack_freezes_as_rkt_does() -> None:
    # The stamp refuses a protocol whose hash `rkt freeze` and `rkt check` disagree on.
    assert (TEMPLATE / "kit/rules/rigour/study/protocol.py").read_text() == (
        TEMPLATE / "tools/rkt/protocol.py"
    ).read_text()


def test_every_rule_pack_the_readme_names_is_in_the_kit() -> None:
    readme = (TEMPLATE / "kit/rules/README.md").read_text()
    for pack in ("rigour", "ml-training", "fe-simulation", "uq-reliability", "literature-check"):
        assert f"`{pack}`" in readme
        assert (TEMPLATE / "kit/rules" / f"{pack}.md").is_file()
