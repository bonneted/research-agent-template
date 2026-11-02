"""`inquiry`: an inquiry's relations from its `inquiry.yaml`, and the tree below it."""

from pathlib import Path

import pytest
from conftest import Tree, write_yaml
from rkt import inquiry


def test_the_tree_lists_the_root_then_its_cloned_sub_inquiries(tree: Tree) -> None:
    members = inquiry.tree(inquiry.load(tree.root))

    assert [member.label for member in members] == ["demo", "demo/framework"]
    assert members[1].parent_path == tree.root
    assert members[0].parent_path is None
    assert members[1].zotero_collection == "demo/framework"


def test_a_sub_inquiry_not_cloned_is_skipped(tree: Tree) -> None:
    write_yaml(
        tree.root / "inquiry.yaml",
        inquiries=[
            {"name": "framework", "url": tree.urls["framework"]},
            {"name": "elsewhere", "url": "https://example.org/elsewhere.git"},
        ],
    )

    members = inquiry.tree(inquiry.load(tree.root))

    assert [member.name for member in members] == ["demo", "framework"]


def test_find_walks_up_to_the_nearest_inquiry(tree: Tree) -> None:
    assert inquiry.find(tree.child / "docs" / "wiki") == tree.child.resolve()
    assert inquiry.find(tree.root / "docs") == tree.root.resolve()


def test_find_outside_any_inquiry_says_how_to_start_one(tmp_path: Path) -> None:
    with pytest.raises(inquiry.InquiryError, match="rkt init"):
        inquiry.find(tmp_path)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"colour": "blue"}, "unknown keys: colour"),
        ({"inquiries": [{"name": "Bad Name", "url": "x"}]}, "not lowercase"),
        ({"inquiries": [{"name": "a"}]}, "needs a name and a url"),
        ({"rule_packs": "rigour"}, "rule_packs must be a list"),
        (
            {"inquiries": [{"name": "a", "url": "x"}, {"name": "a", "url": "y"}]},
            "listed twice: a",
        ),
    ],
)
def test_a_malformed_inquiry_yaml_is_refused(
    tree: Tree, changes: dict, message: str
) -> None:
    write_yaml(tree.root / "inquiry.yaml", **changes)

    with pytest.raises(inquiry.InquiryError, match=message):
        inquiry.load(tree.root)
