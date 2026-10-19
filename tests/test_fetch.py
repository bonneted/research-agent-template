"""`fetch`, run on a project in a temporary folder.

A local bare repository stands in for a code resource's remote and fake sources for the
web; each test checks only `resources/`, the report and success.
"""

from pathlib import Path

import pytest
from conftest import git
from fetch import retrieve
from fetch.cli import fetch, main

PDF = b"%PDF-1.7 a paper"

BIBLIOGRAPHY = """% Exported from Zotero with Better BibTeX
@string{jmps = {Journal of the Mechanics and Physics of Solids}}

@article{raissi2019,
  title = {Physics-informed neural networks},
  doi = {10.1016/j.jcp.2018.10.045},
}

@misc{karniadakis2021,
  title = {Physics-informed machine learning},
  eprint = {2101.00001},
  archiveprefix = {arXiv},
}

@phdthesis{doe2025Thesis,
  title = {A thesis},
}
"""

# The sha256 of b"abc", from FIPS 180-2's worked example.
ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class Fake:
    """A source holding the PDFs of some citekeys, failing on others."""

    def __init__(self, name, has=(), fails=()):
        self.name = name
        self.has = set(has)
        self.fails = set(fails)
        self.asked: list[str] = []

    def retrieve(self, entry):
        self.asked.append(entry.citekey)
        if entry.citekey in self.fails:
            raise retrieve.RetrievalError("unreachable")
        return PDF if entry.citekey in self.has else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    (path / "resources").mkdir(parents=True)
    return path


def remote(tmp_path: Path, name: str) -> tuple[str, str, Path]:
    """A code repository whose head has moved past its first commit; returns its URL,
    that commit and a working clone to push more from.
    """
    work = tmp_path / f"{name}-work"
    work.mkdir()
    git("init", "--quiet", cwd=work)
    (work / "README.md").write_text(f"# {name}\n")
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", "Initial commit", cwd=work)
    first = git("rev-parse", "HEAD", cwd=work)
    bare = tmp_path / f"{name}.git"
    git("clone", "--quiet", "--bare", str(work), str(bare), cwd=tmp_path)
    git("remote", "add", "origin", str(bare), cwd=work)
    push(work, "later.txt")
    return bare.as_uri(), first, work


def push(work: Path, file: str) -> str:
    """Push one more commit from `work`; returns it."""
    (work / file).write_text(f"{file}\n")
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", f"Add {file}", cwd=work)
    git("push", "--quiet", "origin", "HEAD", cwd=work)
    return git("rev-parse", "HEAD", cwd=work)


def write_resources(project: Path, code=(), data=()) -> None:
    """The project's `resources.yaml`.

    A code resource is `(name, url, commit)`, or `(name, url, commit, citekey)` for the
    source form of that document; a data resource is `(name, sha256)`.
    """
    lines = ["code:"]
    for name, url, commit, *source_of in code:
        lines += [f"  - name: {name}", f"    url: {url}", f'    commit: "{commit}"']
        lines += [f"    source_of: {citekey}" for citekey in source_of]
    lines += ["data:"]
    for name, sha256 in data:
        lines += [
            f"  - name: {name}",
            "    source: the lab's shared drive",
            f'    sha256: "{sha256}"',
        ]
    (project / "resources.yaml").write_text("\n".join(lines) + "\n")


def test_retrieved_pdf_is_saved_under_its_citekey(project: Path) -> None:
    (project / "references.bib").write_text(BIBLIOGRAPHY)

    lines, ok = fetch(project, [Fake("a", has={"raissi2019"})])

    assert ok
    assert (project / "resources/papers/raissi2019.pdf").read_bytes() == PDF
    assert "papers/raissi2019.pdf retrieved" in lines
    assert "  papers/doe2025Thesis.pdf" in lines
    assert not list((project / "resources/papers").glob(".*"))


def test_sources_are_tried_in_order_until_one_has_it(project: Path) -> None:
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    first, second = Fake("first", has={"raissi2019"}), Fake("second")

    fetch(project, [first, second])

    assert "raissi2019" in first.asked and "raissi2019" not in second.asked
    assert "doe2025Thesis" in second.asked


def test_failures_fall_through_to_the_missing_list(project: Path) -> None:
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    failing = Fake("broken", fails={"raissi2019", "doe2025Thesis"})
    fallback = Fake("fallback", has={"karniadakis2021"})

    lines, ok = fetch(project, [failing, fallback])

    assert ok
    assert "  papers/raissi2019.pdf" in lines
    assert (project / "resources/papers/karniadakis2021.pdf").exists()
    assert any("broken: unreachable" in line for line in lines)


def test_document_already_there_is_not_asked_for(project: Path) -> None:
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    (project / "resources/papers").mkdir()
    (project / "resources/papers/raissi2019.pdf").write_bytes(b"mine")
    source = Fake("a")

    lines, _ = fetch(project, [source])

    assert "raissi2019" not in source.asked
    assert "  papers/raissi2019.pdf" not in lines


def test_bibliography_keys_are_read_from_entries_only(project: Path) -> None:
    (project / "references.bib").write_text(
        "% @article{commented2020,\n@misc{../escape,\n  title = {x},\n}\n"
    )

    lines, ok = fetch(project, [])

    assert not ok
    assert not any("commented2020" in line for line in lines)
    assert any(line.startswith("FAILED:") and "'../escape'" in line for line in lines)


def test_code_resource_is_cloned_at_its_pinned_commit(
    project: Path, tmp_path: Path
) -> None:
    url, first, _ = remote(tmp_path, "solver")
    write_resources(project, code=[("solver", url, first)])

    lines, ok = fetch(project, [])

    assert ok, lines
    clone = project / "resources/code/solver"
    assert git("rev-parse", "HEAD", cwd=clone) == first
    assert not (clone / "later.txt").exists()
    assert "code/solver cloned" in lines


def test_second_fetch_leaves_the_clone_alone_without_its_remote(
    project: Path, tmp_path: Path
) -> None:
    url, first, _ = remote(tmp_path, "solver")
    write_resources(project, code=[("solver", url, first)])
    fetch(project, [])
    (tmp_path / "solver.git").rename(tmp_path / "gone.git")

    lines, ok = fetch(project, [])

    assert ok, lines
    assert [line for line in lines if not line.startswith("zotero: skipped")] == []


def test_bumped_pin_moves_the_clone_to_it(project: Path, tmp_path: Path) -> None:
    url, first, work = remote(tmp_path, "solver")
    write_resources(project, code=[("solver", url, first)])
    fetch(project, [])
    newer = push(work, "newer.txt")
    write_resources(project, code=[("solver", url, newer)])

    lines, ok = fetch(project, [])

    assert ok, lines
    assert git("rev-parse", "HEAD", cwd=project / "resources/code/solver") == newer
    assert f"code/solver moved to {newer[:12]}" in lines


def test_clone_with_uncommitted_changes_is_not_moved(
    project: Path, tmp_path: Path
) -> None:
    url, first, work = remote(tmp_path, "solver")
    write_resources(project, code=[("solver", url, first)])
    fetch(project, [])
    clone = project / "resources/code/solver"
    (clone / "README.md").write_text("edited\n")
    newer = push(work, "newer.txt")
    write_resources(project, code=[("solver", url, newer)])

    lines, ok = fetch(project, [])

    assert not ok
    assert (
        f"FAILED: code/solver: uncommitted changes in the clone, left at {first[:12]}"
        in lines
    )
    assert git("rev-parse", "HEAD", cwd=clone) == first
    assert (clone / "README.md").read_text() == "edited\n"


def test_unreachable_commit_fails_and_leaves_no_clone(
    project: Path, tmp_path: Path
) -> None:
    url, _, _ = remote(tmp_path, "solver")
    write_resources(project, code=[("solver", url, "0" * 40)])

    lines, ok = fetch(project, [])

    assert not ok
    assert any(line.startswith("FAILED: code/solver:") for line in lines)
    assert list((project / "resources/code").iterdir()) == []


def test_unquoted_commit_read_as_a_number_is_reported(project: Path) -> None:
    (project / "resources.yaml").write_text(
        "code:\n  - name: solver\n    url: somewhere\n    commit: 0123456\n"
    )

    lines, ok = fetch(project, [])

    assert not ok
    assert any("YAML reads as a number: write it in quotes" in line for line in lines)


def test_malformed_resource_list_still_lists_missing_documents(project: Path) -> None:
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    (project / "resources.yaml").write_text("code: not a list\n")

    lines, ok = fetch(project, [])

    assert not ok
    assert any(line.startswith("FAILED: resources.yaml") for line in lines)
    assert "  papers/raissi2019.pdf" in lines


def test_data_resource_with_its_checksum_passes(project: Path) -> None:
    (project / "resources/data").mkdir()
    (project / "resources/data/plate.h5").write_bytes(b"abc")
    write_resources(project, data=[("plate.h5", ABC)])

    lines, ok = fetch(project, [])

    assert ok, lines
    assert [line for line in lines if not line.startswith("zotero: skipped")] == []


def test_data_resource_with_a_wrong_checksum_is_reported(project: Path) -> None:
    (project / "resources/data").mkdir()
    (project / "resources/data/plate.h5").write_bytes(b"abd")
    write_resources(project, data=[("plate.h5", ABC)])

    lines, ok = fetch(project, [])

    assert not ok
    line = next(line for line in lines if "plate.h5" in line)
    assert line.startswith("FAILED: data/plate.h5")
    assert "checksum" in line and ABC in line


def test_missing_data_is_listed_with_where_to_get_it(project: Path) -> None:
    write_resources(project, data=[("plate.h5", ABC)])

    lines, ok = fetch(project, [])

    assert ok
    assert "  data/plate.h5 (from the lab's shared drive)" in lines


def test_source_form_of_a_listed_document_is_cloned(
    project: Path, tmp_path: Path
) -> None:
    url, first, _ = remote(tmp_path, "thesis-tex")
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    write_resources(project, code=[("thesis-tex", url, first, "doe2025Thesis")])

    lines, ok = fetch(project, [])

    assert ok, lines
    assert git("rev-parse", "HEAD", cwd=project / "resources/code/thesis-tex") == first


def test_source_form_of_a_document_the_bibliography_lacks_is_reported(
    project: Path, tmp_path: Path
) -> None:
    url, first, _ = remote(tmp_path, "thesis-tex")
    (project / "references.bib").write_text(BIBLIOGRAPHY)
    write_resources(project, code=[("thesis-tex", url, first, "doe2026Thesis")])

    lines, ok = fetch(project, [])

    assert not ok
    assert (
        "FAILED: resources.yaml: code resource thesis-tex is the source form of "
        "doe2026Thesis, which references.bib does not list"
    ) in lines
    # The clone is still made: only the link is wrong.
    assert git("rev-parse", "HEAD", cwd=project / "resources/code/thesis-tex") == first


def test_command_line_runs_from_a_subfolder_and_exits_on_failure(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    (project / "resources/data").mkdir()
    (project / "resources/data/plate.h5").write_bytes(b"abd")
    write_resources(project, data=[("plate.h5", ABC)])
    (project / "pyproject.toml").write_text("")
    (project / "docs").mkdir()
    monkeypatch.chdir(project / "docs")

    code = main([])

    assert code == 1
    assert "FAILED: data/plate.h5" in capsys.readouterr().out
