"""`ws fetch`, driven end to end in a temporary workspace (see `conftest.py`).

Each test writes resource manifests into the synced clones, runs `ws fetch` from the hub,
and checks only the pool, output and exit code.
"""

import os
import subprocess
from pathlib import Path

import pytest
from conftest import Workspace, git, make_remote


@pytest.fixture
def synced(workspace: Workspace) -> Workspace:
    result = workspace.sync()
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace


def code_remote(workspace: Workspace, name: str) -> tuple[str, str]:
    """A code repository whose head has moved past its first commit; returns its URL and that commit."""
    url = make_remote(workspace.remotes, name)
    work = workspace.tmp / f"{name}-work"
    git("clone", "--quiet", url, str(work), cwd=workspace.tmp)
    first = git("rev-parse", "HEAD", cwd=work)
    (work / "later.txt").write_text("later\n")
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", "Later", cwd=work)
    git("push", "--quiet", cwd=work)
    return url, first


def write_resources(repository: Path, code=(), data=()) -> None:
    """The repository's list of code and data resources, in its working tree.

    A code resource is `(name, url, commit)`, or `(name, url, commit, citekey)` for the
    source form of that document.
    """
    lines = ["code:"]
    for name, url, commit, *source_of in code:
        lines += [f"  - name: {name}", f"    url: {url}", f'    commit: "{commit}"']
        lines += [f"    source_of: {citekey}" for citekey in source_of]
    lines += ["data:"] + [
        line
        for name, sha256 in data
        for line in (
            f"  - name: {name}",
            "    source: the lab's shared drive",
            f'    sha256: "{sha256}"',
        )
    ]
    (repository / "resources.yaml").write_text("\n".join(lines) + "\n")


def test_fetch_clones_a_code_resource_at_its_pinned_commit(synced: Workspace) -> None:
    url, first = code_remote(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, first)])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    clone = synced.pool / "code" / "phd-code"
    assert git("rev-parse", "HEAD", cwd=clone) == first
    assert not (clone / "later.txt").exists()
    assert "code/phd-code cloned" in result.stdout


def test_code_resource_is_cloned_once_for_the_whole_workspace(
    synced: Workspace,
) -> None:
    url, first = code_remote(synced, "phd-code")
    for name in ("demo-hub", "demo-framework"):
        write_resources(synced.root / name, code=[("phd-code", url, first)])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("code/phd-code cloned") == 1


def test_second_fetch_leaves_the_clone_alone_without_its_remote(
    synced: Workspace,
) -> None:
    url, first = code_remote(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, first)])
    synced.fetch()
    (synced.remotes / "phd-code.git").rename(synced.remotes / "gone.git")

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAILED" not in result.stdout
    assert "cloned" not in result.stdout


def push_commit(workspace: Workspace, name: str) -> str:
    """Push one more commit to the code repository `name`; returns it."""
    work = workspace.tmp / f"{name}-work"
    git("pull", "--quiet", cwd=work)
    (work / "newer.txt").write_text("newer\n")
    git("add", ".", cwd=work)
    git("commit", "--quiet", "-m", "Newer", cwd=work)
    git("push", "--quiet", cwd=work)
    return git("rev-parse", "HEAD", cwd=work)


def test_bumped_pin_moves_the_clone_to_it(synced: Workspace) -> None:
    url, first = code_remote(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, first)])
    synced.fetch()
    newer = push_commit(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, newer)])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    clone = synced.pool / "code" / "phd-code"
    assert git("rev-parse", "HEAD", cwd=clone) == newer
    assert f"code/phd-code moved to {newer[:12]}" in result.stdout


def test_clone_follows_the_newest_pin_of_the_workspace(synced: Workspace) -> None:
    url, first = code_remote(synced, "phd-code")
    newer = push_commit(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, newer)])
    study = synced.root / "demo-framework"
    write_resources(study, code=[("phd-code", url, first)])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    clone = synced.pool / "code" / "phd-code"
    assert git("rev-parse", "HEAD", cwd=clone) == newer
    assert result.stdout.count("code/phd-code cloned") == 1
    line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("demo-framework:")
    )
    assert (
        f"code/phd-code is at newer {newer[:12]}, this repository pins {first}" in line
    )


def test_clone_with_uncommitted_changes_is_not_moved(synced: Workspace) -> None:
    url, first = code_remote(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, first)])
    synced.fetch()
    clone = synced.pool / "code" / "phd-code"
    (clone / "README.md").write_text("edited\n")
    newer = push_commit(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, newer)])

    result = synced.fetch()

    assert result.returncode != 0
    assert (
        "demo-hub: FAILED: code/phd-code: uncommitted changes in the pool's clone, "
        f"left at {first[:12]}"
    ) in result.stdout
    assert git("rev-parse", "HEAD", cwd=clone) == first
    assert (clone / "README.md").read_text() == "edited\n"


def test_unreachable_commit_fails_and_leaves_no_clone(synced: Workspace) -> None:
    url, _ = code_remote(synced, "phd-code")
    write_resources(synced.hub, code=[("phd-code", url, "0" * 40)])

    result = synced.fetch()

    assert result.returncode != 0
    assert "demo-hub: FAILED: code/phd-code:" in result.stdout
    assert list((synced.pool / "code").iterdir()) == []


def test_unquoted_commit_read_as_a_number_is_reported(synced: Workspace) -> None:
    (synced.hub / "resources.yaml").write_text(
        "code:\n  - name: phd-code\n    url: somewhere\n    commit: 0123456\n"
    )

    result = synced.fetch()

    assert result.returncode != 0
    assert (
        "has a commit that YAML reads as a number: write it in quotes" in result.stdout
    )


# The sha256 of b"abc", from FIPS 180-2's worked example.
ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_data_resource_with_its_checksum_passes(synced: Workspace) -> None:
    (synced.pool / "data").mkdir()
    (synced.pool / "data" / "plate.h5").write_bytes(b"abc")
    write_resources(synced.hub, data=[("plate.h5", ABC)])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAILED" not in result.stdout


def test_data_resource_with_a_wrong_checksum_is_reported(synced: Workspace) -> None:
    (synced.pool / "data").mkdir()
    (synced.pool / "data" / "plate.h5").write_bytes(b"abd")
    write_resources(synced.hub, data=[("plate.h5", ABC)])

    result = synced.fetch()

    assert result.returncode != 0
    line = next(line for line in result.stdout.splitlines() if "plate.h5" in line)
    assert line.startswith("demo-hub: FAILED: data/plate.h5")
    assert "checksum" in line and ABC in line


BIBLIOGRAPHY = """% Exported from Zotero with Better BibTeX
@string{jmps = {Journal of the Mechanics and Physics of Solids}}

@article{raissi2019,
  title = {Physics-informed neural networks},
  doi = {10.1016/j.jcp.2018.10.045},
}

@phdthesis{bonnet2025Thesis,
  title = {A thesis},
}
"""


def test_missing_documents_and_data_are_listed_with_a_command_that_copies_them_in(
    synced: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    study = synced.root / "demo-framework"
    (study / "references.bib").write_text(BIBLIOGRAPHY)
    write_resources(study, data=[("plate.h5", ABC)])
    (synced.pool / "papers").mkdir()
    (synced.pool / "papers" / "raissi2019.pdf").write_text("pdf")
    laptop = synced.tmp / "laptop-pool"
    for path, content in {
        "papers/bonnet2025Thesis.pdf": b"thesis",
        "data/plate.h5": b"abc",
    }.items():
        (laptop / path).parent.mkdir(parents=True, exist_ok=True)
        (laptop / path).write_bytes(content)
    monkeypatch.setenv("DEMO_SSH_HOST", "compute")

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "demo-hub: 1 missing" in result.stdout
    assert "demo-framework: 2 missing" in result.stdout
    command = result.stdout[result.stdout.index("rsync") :]
    assert f"compute:{synced.pool}/" in command
    # Run on the laptop; on one machine, the copy is local.
    subprocess.run(
        ["bash", "-c", command.replace("compute:", "")],
        env={**os.environ, "DEMO_RESOURCES": str(laptop)},
        check=True,
        capture_output=True,
    )
    assert (synced.pool / "papers" / "bonnet2025Thesis.pdf").read_bytes() == b"thesis"
    assert (synced.pool / "data" / "plate.h5").read_bytes() == b"abc"
    after = synced.fetch()
    assert after.returncode == 0, after.stdout + after.stderr
    assert "missing from the pool" not in after.stdout
    assert not any(line.endswith(" missing") for line in after.stdout.splitlines())


def test_malformed_resource_list_still_lists_missing_documents(
    synced: Workspace,
) -> None:
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    (synced.hub / "resources.yaml").write_text("code: not a list\n")

    result = synced.fetch()

    assert result.returncode != 0
    assert "demo-hub: FAILED:" in result.stdout
    assert "papers/raissi2019.pdf" in result.stdout.splitlines()


def test_bibliography_keys_are_read_from_entries_only(synced: Workspace) -> None:
    (synced.hub / "references.bib").write_text(
        "% @article{commented2020,\n@misc{../escape,\n  title = {x},\n}\n"
    )

    result = synced.fetch()

    assert result.returncode != 0
    assert "commented2020" not in result.stdout
    assert "demo-hub: FAILED:" in result.stdout and "'../escape'" in result.stdout
    assert "papers/../escape.pdf" not in result.stdout


def test_source_form_of_a_listed_document_is_cloned(synced: Workspace) -> None:
    url, first = code_remote(synced, "phd-thesis")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_resources(synced.hub, code=[("phd-thesis", url, first, "bonnet2025Thesis")])

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert git("rev-parse", "HEAD", cwd=synced.pool / "code" / "phd-thesis") == first


def test_source_form_of_a_document_the_bibliography_lacks_is_reported(
    synced: Workspace,
) -> None:
    url, first = code_remote(synced, "phd-thesis")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_resources(synced.hub, code=[("phd-thesis", url, first, "bonnet2026Thesis")])

    result = synced.fetch()

    assert result.returncode != 0
    assert (
        "demo-hub: FAILED: resources.yaml: code resource phd-thesis is the source "
        "form of bonnet2026Thesis, which references.bib does not list"
    ) in result.stdout.splitlines()
    # The clone is still made: only the link is wrong.
    assert git("rev-parse", "HEAD", cwd=synced.pool / "code" / "phd-thesis") == first


def write_code_of(repository: Path, url: str, commit: str, code_of: str) -> None:
    """A resource manifest whose one code resource, `jaxpi2`, has `code_of: <code_of>` as written."""
    (repository / "resources.yaml").write_text(
        f"code:\n  - name: jaxpi2\n    url: {url}\n"
        f'    commit: "{commit}"\n    code_of: {code_of}\n'
    )


def test_code_of_listed_documents_is_cloned(synced: Workspace) -> None:
    url, first = code_remote(synced, "jaxpi2")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_code_of(synced.hub, url, first, "[raissi2019, bonnet2025Thesis]")

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert git("rev-parse", "HEAD", cwd=synced.pool / "code" / "jaxpi2") == first


def test_code_of_a_document_the_bibliography_lacks_is_reported(
    synced: Workspace,
) -> None:
    url, first = code_remote(synced, "jaxpi2")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_code_of(synced.hub, url, first, "[raissi2019, wang2026pinns]")

    result = synced.fetch()

    assert result.returncode != 0
    assert (
        "demo-hub: FAILED: resources.yaml: code resource jaxpi2 is the code of "
        "wang2026pinns, which references.bib does not list"
    ) in result.stdout.splitlines()
    assert "raissi2019, which" not in result.stdout
    assert git("rev-parse", "HEAD", cwd=synced.pool / "code" / "jaxpi2") == first


def test_code_of_one_citekey_needs_no_list(synced: Workspace) -> None:
    url, first = code_remote(synced, "jaxpi2")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_code_of(synced.hub, url, first, "wang2026pinns")

    result = synced.fetch()

    assert (
        "demo-hub: FAILED: resources.yaml: code resource jaxpi2 is the code of "
        "wang2026pinns, which references.bib does not list"
    ) in result.stdout.splitlines()


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ("{a: b}", "has a code_of that is not a citekey or a list of citekeys"),
        ("[raissi2019, 3]", "has a code_of that is not a citekey or a list of citekeys"),
        (
            "raissi2019\n    source_of: bonnet2025Thesis",
            (
                "has both a source_of and a code_of: a repository is a document's "
                "source form or its code, not both"
            ),
        ),
    ],
)
def test_malformed_code_of_is_reported(
    synced: Workspace, extra: str, message: str
) -> None:
    url, first = code_remote(synced, "jaxpi2")
    (synced.hub / "references.bib").write_text(BIBLIOGRAPHY)
    write_code_of(synced.hub, url, first, extra)

    result = synced.fetch()

    assert result.returncode != 0
    assert f"code resource jaxpi2 {message}" in result.stdout
