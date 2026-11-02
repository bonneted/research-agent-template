"""`rkt check`: each rule a machine can tell, broken once in the temporary tree."""

from pathlib import Path

import pytest
from conftest import Tree, commit_all, git, write_yaml
from rkt import check, inquiry


def run(tree: Tree) -> tuple[list[str], bool]:
    return check.check(inquiry.tree(inquiry.load(tree.root)))


def failures(tree: Tree) -> list[str]:
    return [line for line in run(tree)[0] if ": FAILED: " in line]


def note(folder: Path, relative: str, text: str) -> Path:
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def index_line(folder: Path, index: str, line: str) -> None:
    """Add a line to an index, so the note it links is reachable."""
    path = folder / index
    path.write_text(path.read_text() + line + "\n")


def concept(folder: Path, name: str, body: str) -> None:
    note(folder, f"docs/wiki/concepts/{name}.md", f"# {name}\n\n{body}\n")
    index_line(folder, "docs/wiki/concepts/index.md", f"- [{name}]({name}.md): a concept")


def test_a_tree_fresh_from_the_kit_passes(tree: Tree) -> None:
    lines, ok = run(tree)

    assert ok, lines
    assert lines == ["demo: ok", "demo/framework: ok"]


def test_the_command_checks_the_tree_from_the_root(tree: Tree) -> None:
    result = tree.run("check", "--tree")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["demo: ok", "demo/framework: ok"]


def test_a_link_to_nothing_fails(tree: Tree) -> None:
    concept(tree.root, "sphere", "See [the shell](shell.md).")

    assert failures(tree) == [
        "demo: FAILED: docs/wiki/concepts/sphere.md:3: shell.md does not exist"
    ]


def test_a_wikilink_fails(tree: Tree) -> None:
    concept(tree.root, "sphere", "See [[shell]].")

    assert failures(tree) == [
        ("demo: FAILED: docs/wiki/concepts/sphere.md:3: [[shell]] is a wikilink: "
        "use a relative Markdown link")
    ]


def test_links_up_to_the_parent_and_down_to_a_child_pass(tree: Tree) -> None:
    concept(tree.root, "sphere", "Shown in [the framework](../../../inquiries/framework/docs/wiki/index.md).")
    concept(tree.child, "ring", "Used by [the demo](../../../../../docs/wiki/index.md).")

    lines, ok = run(tree)

    assert ok, lines


def test_a_sideways_link_to_a_sibling_fails(tree: Tree) -> None:
    concept(tree.child, "ring", "Like [the other](../../../../other/docs/wiki/index.md).")

    assert failures(tree) == [
        ("demo/framework: FAILED: docs/wiki/concepts/ring.md:3: "
        "../../../../other/docs/wiki/index.md leaves this inquiry, its parent and its "
        "children: link through the common ancestor instead")
    ]


def test_links_in_comments_and_code_are_examples(tree: Tree) -> None:
    concept(tree.root, "sphere", "<!-- [x](missing.md) -->\n\n`[y](missing.md)`")

    assert run(tree)[1]


def test_a_note_no_index_reaches_fails(tree: Tree) -> None:
    note(tree.root, "docs/wiki/concepts/orphan.md", "# Orphan\n")

    assert failures(tree) == [
        ("demo: FAILED: docs/wiki/concepts/orphan.md is not reachable from "
        "docs/wiki/index.md: link it from its folder's index")
    ]


def test_a_notes_folder_without_its_index_fails(tree: Tree) -> None:
    note(tree.root, "docs/wiki/methods/fdm.md", "# FDM\n")
    index_line(tree.root, "docs/wiki/index.md", "- [FDM](methods/fdm.md)")

    assert failures(tree) == ["demo: FAILED: docs/wiki/methods/ has notes but no index.md"]


def test_a_sub_inquiry_without_a_route_fails(tree: Tree) -> None:
    index = tree.root / "docs/wiki/index.md"
    index.write_text(index.read_text().replace("- [framework]", "- framework, unlinked"))

    assert "demo: FAILED: docs/wiki/index.md: sub-inquiry framework has no route " \
        "under ## Sub-inquiries" in failures(tree)


def test_a_route_to_an_unlisted_inquiry_fails(tree: Tree) -> None:
    write_yaml(tree.root / "inquiry.yaml", inquiries=[])

    # Unlisted, the folder is no longer a child: the route's link is sideways too.
    assert (
        "demo: FAILED: docs/wiki/index.md: routes to framework, which inquiry.yaml "
        "does not list"
    ) in failures(tree)


def test_an_unknown_citekey_fails_and_one_from_an_ancestor_passes(tree: Tree) -> None:
    (tree.root / "references.bib").write_text(
        "@article{smith2020,\n  doi = {10.1/x},\n}\n"
    )
    concept(tree.child, "ring", "As in [@smith2020, p. 3] and [@jones2021, p. 4].")

    assert failures(tree) == [
        ("demo/framework: FAILED: docs/wiki/concepts/ring.md:3: [@jones2021] is not in "
        "references.bib")
    ]


def test_a_reference_without_an_identifier_is_a_warning(tree: Tree) -> None:
    (tree.root / "references.bib").write_text("@phdthesis{bonnet2025,\n  title = {T},\n}\n")

    lines, ok = run(tree)

    assert ok
    assert lines[0].startswith(
        "demo: WARNING: references.bib: bonnet2025 has no DOI, arXiv id, URL or ISBN"
    )


FINDING = """---
status: {status}
tried: {tried}
evidence:
{evidence}
{extra}---

# A claim
"""


def finding(folder: Path, name: str, status: str = "hint", tried: object = 3,
            evidence: str = "  - kind: source\n    citekey: smith2020\n    page: 7\n",
            extra: str = "") -> None:
    (folder / "references.bib").write_text("@article{smith2020,\n  doi = {10.1/x},\n}\n")
    note(folder, f"docs/findings/{name}.md", FINDING.format(
        status=status, tried=tried, evidence=evidence.rstrip("\n"), extra=extra))
    index_line(folder, "docs/findings/index.md", f"- [{name}]({name}.md): a claim ({status})")


def test_a_hint_with_its_denominator_passes(tree: Tree) -> None:
    finding(tree.root, "a-claim")

    assert run(tree)[1]


def test_a_finding_without_its_denominator_fails(tree: Tree) -> None:
    finding(tree.root, "a-claim", tried="null")

    assert failures(tree) == [
        ("demo: FAILED: docs/findings/a-claim.md: tried must be the number of variants, "
        "analyses or runs tried to reach the claim (rule 10)")
    ]


def child_finding(tree: Tree, status: str) -> str:
    """A finding committed in the sub-inquiry; returns its permalink."""
    finding(tree.child, "a-sub-claim", status=status)
    sha = commit_all(tree.child, "A finding")
    return f"{tree.urls['framework']}/-/blob/{sha}/docs/findings/a-sub-claim.md"


CONFIRMED = (
    "reviewed:\n  date: 2026-11-02\n  verdict: upheld\n  notes: held\n"
    "approved: 2026-11-02\n"
)


def test_a_confirmed_finding_on_a_hint_of_a_sub_inquiry_fails(tree: Tree) -> None:
    link = child_finding(tree, "hint")
    finding(
        tree.root, "a-claim", status="confirmed",
        evidence=f"  - kind: sub-inquiry\n    finding: {link}\n    status: hint\n",
        extra=CONFIRMED,
    )

    assert failures(tree) == [
        ("demo: FAILED: docs/findings/a-claim.md: confirmed, but rests on a sub-inquiry "
        "finding that is hint: the tree never strengthens a claim (rule 11)")
    ]


def test_a_sub_inquiry_status_that_differs_at_its_commit_fails(tree: Tree) -> None:
    link = child_finding(tree, "hint")
    finding(
        tree.root, "a-claim",
        evidence=f"  - kind: sub-inquiry\n    finding: {link}\n    status: confirmed\n",
    )

    assert failures(tree) == [
        (f"demo: FAILED: docs/findings/a-claim.md evidence 1: says the sub-inquiry's "
        f"finding is confirmed, but it is hint at {link.split('/blob/')[1][:12]}")
    ]


def test_a_confirmed_finding_needs_the_users_approval(tree: Tree) -> None:
    link = child_finding(tree, "hint")
    git("checkout", "--quiet", "-b", "confirm", cwd=tree.child)
    finding(tree.child, "a-sub-claim", status="confirmed", extra=CONFIRMED)
    sha = commit_all(tree.child, "Confirmed")
    link = link.rsplit("/blob/", 1)[0] + f"/blob/{sha}/docs/findings/a-sub-claim.md"
    finding(
        tree.root, "a-claim", status="confirmed",
        evidence=f"  - kind: sub-inquiry\n    finding: {link}\n    status: confirmed\n",
        extra=CONFIRMED.replace("approved: 2026-11-02\n", ""),
    )

    assert [line for line in failures(tree) if line.startswith("demo: ")] == [
        ("demo: FAILED: docs/findings/a-claim.md: confirmed needs the date the user "
        "approved it in approved (rule 12)")
    ]


def test_a_sub_inquiry_that_drops_an_inherited_rule_pack_fails(tree: Tree) -> None:
    write_yaml(tree.root / "inquiry.yaml", rule_packs=["rigour"])

    assert failures(tree) == [
        ("demo/framework: FAILED: the parent selects the rule pack rigour: "
        "a sub-inquiry keeps it")
    ]


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ("type: explore\n", "declares no consolidation: scout, build, publish (rule 2)"),
        ("consolidation: scout\n", "declares no type: explore or confirm"),
    ],
)
def test_a_phase_declares_its_type_and_level(tree: Tree, config: str, message: str) -> None:
    note(tree.root, "phases/01-sphere/config.yaml", config)
    note(tree.root, "docs/wiki/phases/01-sphere.md", "# 01-sphere\n")
    index_line(tree.root, "docs/wiki/phases/index.md", "- [01-sphere](01-sphere.md)")

    assert failures(tree) == [f"demo: FAILED: phases/01-sphere/config.yaml {message}"]
