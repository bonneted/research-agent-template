"""`refs`: the bibliography pulled from Zotero, and references added to it.

Driven in-process against a fake web (see `fakes`); the command line itself is run only
where no request goes out.
"""

from pathlib import Path

import pytest
from fakes import Web
from fetch import lookup, manifest, refs, zotero
from fetch.cli import fetch

RAISSI = {
    "itemType": "journalArticle",
    "title": "Physics-informed neural networks: A deep learning framework",
    "creators": [
        {"creatorType": "author", "firstName": "Maziar", "lastName": "Raissi"},
        {"creatorType": "author", "firstName": "George Em", "lastName": "Karniadakis"},
    ],
    "publicationTitle": "Journal of Computational Physics",
    "date": "2019-02-01",
    "volume": "378",
    "pages": "686-707",
    "DOI": "10.1016/j.jcp.2018.10.045",
    "url": "https://doi.org/10.1016/j.jcp.2018.10.045",
    "abstractNote": "We introduce physics-informed neural networks & more.",
    "citationKey": "raissi2019physics",
}

KARNIADAKIS = {
    "itemType": "preprint",
    "title": "Physics-informed machine learning",
    "creators": [
        {"creatorType": "author", "firstName": "George Em", "lastName": "Karniadakis"}
    ],
    "date": "2021",
    "repository": "arXiv",
    "archiveID": "arXiv:2101.00001",
    "DOI": "10.48550/arXiv.2101.00001",
    "url": "http://arxiv.org/abs/2101.00001v2",
    "citationKey": "karniadakis2021physics",
}

CROSSREF_RAISSI = {
    "type": "journal-article",
    "DOI": "10.1016/j.jcp.2018.10.045",
    "title": ["Physics-informed neural networks: A deep learning framework"],
    "author": [
        {"given": "M.", "family": "Raissi"},
        {"given": "G.E.", "family": "Karniadakis"},
    ],
    "container-title": ["Journal of Computational Physics"],
    "published": {"date-parts": [[2019, 2]]},
    "volume": "378",
    "page": "686-707",
    "ISSN": ["0021-9991"],
    "publisher": "Elsevier BV",
    "URL": "https://doi.org/10.1016/j.jcp.2018.10.045",
    "abstract": "<jats:p>We introduce physics-informed neural networks.</jats:p>",
}

PDF = b"%PDF-1.7 a paper"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project whose resource manifest names the collection `Projects/beam`."""
    path = tmp_path / "project"
    (path / "resources").mkdir(parents=True)
    (path / "pyproject.toml").write_text("")
    (path / "resources.yaml").write_text("zotero_collection: Projects/beam\n")
    return path


@pytest.fixture
def web() -> Web:
    """A library with the project's collection, and another one."""
    web = Web()
    web.beam = web.collection("beam", web.collection("Projects"))
    web.other = web.collection("Other project")
    return web


def bibliography(project: Path) -> dict[str, manifest.Entry]:
    return manifest.entries((project / "references.bib").read_text())


def without_citekey(item: dict) -> dict:
    return {key: value for key, value in item.items() if key != "citationKey"}


def test_pull_writes_the_collection_in_the_fixed_form(project: Path, web: Web) -> None:
    web.item([web.beam], **RAISSI)

    lines, ok = refs.pull(project, web.library())

    assert ok, lines
    assert (project / "references.bib").read_text() == (
        "% Written by `uv run refs pull` from the Zotero collection Projects/beam.\n"
        "% Add a reference with `uv run refs add`, or in Zotero, never here.\n"
        "\n"
        "@article{raissi2019physics,\n"
        "  author = {Raissi, Maziar and Karniadakis, George Em},\n"
        "  title = {Physics-informed neural networks: A deep learning framework},\n"
        "  journal = {Journal of Computational Physics},\n"
        "  year = {2019},\n"
        "  month = {feb},\n"
        "  volume = {378},\n"
        "  pages = {686--707},\n"
        "  doi = {10.1016/j.jcp.2018.10.045},\n"
        "  url = {https://doi.org/10.1016/j.jcp.2018.10.045},\n"
        "  abstract = {We introduce physics-informed neural networks \\& more.},\n"
        "}\n"
    )


def test_entries_are_sorted_and_carry_what_fetch_reads(project: Path, web: Web) -> None:
    web.item([web.beam], **RAISSI)
    web.item([web.beam], **KARNIADAKIS)
    web.item([web.other], **{**RAISSI, "citationKey": "elsewhere2020"})

    refs.pull(project, web.library())

    found = bibliography(project)
    assert list(found) == ["karniadakis2021physics", "raissi2019physics"]
    assert found["karniadakis2021physics"].arxiv == "2101.00001"
    assert found["raissi2019physics"].doi == "10.1016/j.jcp.2018.10.045"


def test_entry_gone_from_the_collection_is_removed_and_a_cited_one_warned(
    project: Path, web: Web
) -> None:
    web.item([web.beam], **RAISSI)
    (project / "references.bib").write_text(
        "@article{raissi2019physics,\n}\n"
        "@article{forgotten2010,\n}\n"
        "@article{cited-one2011,\n}\n"
    )
    (project / "docs/wiki").mkdir(parents=True)
    (project / "docs/wiki/note.md").write_text(
        "As shown [@raissi2019physics; @cited-one2011, p. 3].\n"
        "Not a citation: @forgotten2010s.\n"
    )

    lines, ok = refs.pull(project, web.library())

    assert ok, lines
    assert list(bibliography(project)) == ["raissi2019physics"]
    assert "references.bib: removed cited-one2011, forgotten2010" in lines
    assert (
        "WARNING: cited-one2011 is no longer in the collection, "
        "but docs/wiki/note.md cites it"
    ) in lines
    assert not any("WARNING: forgotten2010" in line for line in lines)


def test_citekey_pinned_in_extra_is_kept(project: Path, web: Web) -> None:
    web.item(
        [web.beam],
        **without_citekey(RAISSI),
        extra="tex.ids: other\nCitation Key: raissiPINN2019",
    )

    refs.pull(project, web.library())

    assert list(bibliography(project)) == ["raissiPINN2019"]


def test_item_without_citekey_gets_one_unique_in_the_library_and_written_back(
    project: Path, web: Web
) -> None:
    web.item([web.other], **RAISSI)
    new = web.item(
        [web.beam],
        **{
            **without_citekey(RAISSI),
            "title": "The physics of networks",
            "creators": [
                {"creatorType": "author", "firstName": "Anna", "lastName": "Raissi"}
            ],
        },
    )
    thesis = web.item(
        [web.beam],
        itemType="thesis",
        title="A Thesis on Beams",
        creators=[{"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}],
        date="2026",
        university="A University",
    )

    lines, ok = refs.pull(project, web.library())

    assert ok, lines
    assert web.data(new)["citationKey"] == "raissi2019physicsa"
    assert web.data(thesis)["citationKey"] == "doe2026thesis"
    assert list(bibliography(project)) == ["doe2026thesis", "raissi2019physicsa"]


def test_read_only_key_pulls_but_fails_the_write_back(project: Path, web: Web) -> None:
    web.writable = False
    item = web.item([web.beam], **without_citekey(RAISSI))

    lines, ok = refs.pull(project, web.library())

    assert not ok
    assert "citationKey" not in web.data(item)
    assert list(bibliography(project)) == ["raissi2019physics"]
    assert any(line.startswith("FAILED: the Zotero key is read-only") for line in lines)


def test_collection_can_be_named_by_key(project: Path, web: Web) -> None:
    web.item([web.other], **RAISSI)
    (project / "resources.yaml").write_text(f"zotero_collection: {web.other}\n")

    lines, ok = refs.pull(project, web.library())

    assert ok, lines
    assert list(bibliography(project)) == ["raissi2019physics"]


def test_pull_without_a_named_collection_says_where_to_name_it(
    project: Path, web: Web
) -> None:
    (project / "resources.yaml").write_text("code: []\n")

    with pytest.raises(refs.NoCollection, match="zotero_collection in resources.yaml"):
        refs.pull(project, web.library())


def test_pull_without_configuration_fails_and_keeps_the_bibliography(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    (project / "references.bib").write_text("@article{kept2020,\n}\n")
    (project / "docs").mkdir()
    monkeypatch.chdir(project / "docs")

    code = refs.main(["pull"])

    assert code == 1
    assert "FAILED: no Zotero configuration in " in capsys.readouterr().out
    assert (project / "references.bib").read_text() == "@article{kept2020,\n}\n"


def test_fetch_pulls_before_retrieving(project: Path, web: Web) -> None:
    web.item([web.beam], **RAISSI)

    lines, ok = fetch(project, [], web.library())

    assert ok, lines
    assert "references.bib: 1 entry from Zotero" in lines
    # What the pull wrote is what is retrieved.
    assert "  papers/raissi2019physics.pdf" in lines


def test_fetch_with_zotero_unreachable_skips_the_pull(project: Path, web: Web) -> None:
    web.down = True
    (project / "references.bib").write_text("@article{kept2020,\n}\n")

    lines, ok = fetch(project, [], web.library())

    assert ok, lines
    assert [line for line in lines if line.startswith("zotero:")] == [
        "zotero: skipped (Zotero is unreachable: no route to host)"
    ]
    assert (project / "references.bib").read_text() == "@article{kept2020,\n}\n"
    assert "  papers/kept2020.pdf" in lines


def test_fetch_without_a_named_collection_skips_the_pull(
    project: Path, web: Web
) -> None:
    (project / "resources.yaml").write_text("code: []\n")
    (project / "references.bib").write_text("@article{kept2020,\n}\n")

    lines, ok = fetch(project, [], web.library())

    assert ok, lines
    assert lines[0].startswith("zotero: skipped (name the project's Zotero collection")
    assert (project / "references.bib").read_text() == "@article{kept2020,\n}\n"


def add(project: Path, web: Web, identifier: str):
    return refs.add(project, lookup.identify(identifier), web.library())


def test_add_creates_the_item_from_crossref_in_the_collection_and_pulls(
    project: Path, web: Web
) -> None:
    web.crossref["10.1016/j.jcp.2018.10.045"] = CROSSREF_RAISSI

    lines, ok = add(project, web, "10.1016/J.JCP.2018.10.045")

    assert ok, lines
    [item] = web.items.values()
    data = item["data"]
    assert data["itemType"] == "journalArticle"
    assert data["collections"] == [web.beam]
    assert data["citationKey"] == "raissi2019physics"
    assert data["abstractNote"] == "We introduce physics-informed neural networks."
    assert lines[0] == "added raissi2019physics"
    assert lines[-1] == "run `uv run fetch` to retrieve its PDF"
    assert bibliography(project)["raissi2019physics"].doi == "10.1016/j.jcp.2018.10.045"


def test_add_asks_datacite_for_a_doi_crossref_does_not_know(
    project: Path, web: Web
) -> None:
    web.datacite["10.5281/zenodo.123"] = {
        "doi": "10.5281/zenodo.123",
        "titles": [{"title": "Beam deflection measurements"}],
        "creators": [
            {"name": "Doe, Jane", "givenName": "Jane", "familyName": "Doe"},
            {"name": "A Laboratory", "nameType": "Organizational"},
        ],
        "publisher": "Zenodo",
        "publicationYear": 2024,
        "types": {"resourceTypeGeneral": "Dataset"},
        "descriptions": [
            {"description": "<p>Deflections.</p>", "descriptionType": "Abstract"}
        ],
        "url": "https://zenodo.org/records/123",
    }

    lines, ok = add(project, web, "https://doi.org/10.5281/zenodo.123")

    assert ok, lines
    [item] = web.items.values()
    assert item["data"]["itemType"] == "dataset"
    assert item["data"]["citationKey"] == "doe2024beam"
    assert item["data"]["creators"][1] == {
        "creatorType": "author",
        "name": "A Laboratory",
    }
    assert bibliography(project)["doe2024beam"].doi == "10.5281/zenodo.123"


ARXIV_PAPER = {
    "title": "Physics-informed\n  machine learning",
    "summary": "  Physics meets data.\n",
    "authors": ["George Em Karniadakis", "Ioannis G. Kevrekidis"],
    "published": "2021-01-04T18:00:00Z",
}


@pytest.mark.parametrize(
    "identifier",
    [
        "2101.00001",
        "arXiv:2101.00001v2",
        "https://arxiv.org/abs/2101.00001v2",
        "https://arxiv.org/pdf/2101.00001.pdf",
        "10.48550/arXiv.2101.00001",
    ],
)
def test_add_looks_an_arxiv_identifier_up_in_arxiv(
    project: Path, web: Web, identifier: str
) -> None:
    web.arxiv["2101.00001"] = ARXIV_PAPER

    lines, ok = add(project, web, identifier)

    assert ok, lines
    [item] = web.items.values()
    data = item["data"]
    assert data["itemType"] == "preprint"
    assert data["title"] == "Physics-informed machine learning"
    assert data["citationKey"] == "karniadakis2021physics"
    assert bibliography(project)["karniadakis2021physics"].arxiv == "2101.00001"


@pytest.mark.parametrize(
    "item, identifier",
    [
        (RAISSI, "https://doi.org/10.1016/J.JCP.2018.10.045"),
        (KARNIADAKIS, "arXiv:2101.00001v1"),
        ({**KARNIADAKIS, "archiveID": "", "DOI": ""}, "2101.00001"),
    ],
)
def test_add_reuses_the_item_already_in_the_library(
    project: Path, web: Web, item: dict, identifier: str
) -> None:
    web.item(
        [web.other],
        **{
            **RAISSI,
            "title": "Decoy",
            "citationKey": "decoy",
            "DOI": "10.1016/j.jcp.2018.10.0451",
        },
    )
    existing = web.item([web.other], **item)

    lines, ok = add(project, web, identifier)

    assert ok, lines
    assert len(web.items) == 2
    assert web.data(existing)["collections"] == [web.other, web.beam]
    assert lines[0] == f"added {item['citationKey']}, already in Zotero"
    assert item["citationKey"] in bibliography(project)
    assert not any(
        "crossref" in url or "arxiv.org/api" in url for _, url in web.requests
    )


@pytest.mark.parametrize(
    "identifier", ["https://example.org/thesis.pdf", "Raissi et al. 2019", "hdl:1234/5"]
)
def test_add_refuses_anything_but_a_doi_or_arxiv_identifier(
    project: Path,
    identifier: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.chdir(project)

    code = refs.main(["add", identifier])

    assert code == 1
    out = capsys.readouterr().out
    assert out.startswith("FAILED: ")
    assert "add a thesis, report or slides by hand in Zotero" in out


def test_add_with_a_read_only_key_fails_with_a_clear_message(
    project: Path, web: Web
) -> None:
    web.crossref["10.1016/j.jcp.2018.10.045"] = CROSSREF_RAISSI
    web.writable = False

    with pytest.raises(zotero.ReadOnly, match="the Zotero key is read-only"):
        add(project, web, "10.1016/j.jcp.2018.10.045")

    assert web.items == {}


def test_add_without_zotero_writes_the_looked_up_entry_into_the_bibliography(
    project: Path, web: Web
) -> None:
    (project / "references.bib").write_text("@article{raissi2019physics,\n}\n")
    web.arxiv["2101.00001"] = ARXIV_PAPER

    lines, ok = refs.add_without_zotero(project, lookup.identify("2101.00001"), web)

    assert ok, lines
    assert (
        lines[0]
        == "added karniadakis2021physics to references.bib (no Zotero configuration)"
    )
    found = bibliography(project)
    assert list(found) == ["raissi2019physics", "karniadakis2021physics"]
    assert found["karniadakis2021physics"].arxiv == "2101.00001"
    assert not any("zotero.org" in url for _, url in web.requests)


def test_add_without_zotero_keeps_one_entry_per_reference(
    project: Path, web: Web
) -> None:
    (project / "references.bib").write_text(
        "@article{mine,\n  doi = {10.1016/j.jcp.2018.10.045},\n}\n"
    )

    lines, ok = refs.add_without_zotero(
        project, lookup.identify("10.1016/J.JCP.2018.10.045"), web
    )

    assert ok
    assert lines == ["mine is already in references.bib"]
    assert web.requests == []


class Arxiv:
    """A source that has every PDF."""

    name = "arXiv"

    def retrieve(self, entry):
        return PDF


def test_fetch_attaches_a_retrieved_pdf_to_its_item_when_asked(
    project: Path, web: Web
) -> None:
    item = web.item([web.beam], **RAISSI)

    lines, ok = fetch(project, [Arxiv()], web.library(upload_pdfs=True))

    assert ok, lines
    [attachment] = [
        key
        for key, value in web.items.items()
        if value["data"].get("parentItem") == item
    ]
    assert web.data(attachment)["filename"] == "raissi2019physics.pdf"
    assert web.files[attachment] == PDF
    assert "papers/raissi2019physics.pdf retrieved, attached in Zotero" in lines


def test_upload_is_off_by_default(project: Path, web: Web) -> None:
    web.item([web.beam], **RAISSI)

    fetch(project, [Arxiv()], web.library())

    assert len(web.items) == 1


def test_a_full_zotero_storage_is_a_warning(project: Path, web: Web) -> None:
    web.item([web.beam], **RAISSI)
    web.quota_full = True

    lines, ok = fetch(project, [Arxiv()], web.library(upload_pdfs=True))

    assert ok, lines
    assert (project / "resources/papers/raissi2019physics.pdf").read_bytes() == PDF
    assert (
        "WARNING: papers/raissi2019physics.pdf not attached in Zotero: "
        "its file storage is full"
    ) in lines
    # The attachment made for it is not left empty in the library.
    assert len(web.items) == 1


def test_software_programmers_are_its_authors() -> None:
    from fetch.bibtex import fields

    data = {
        "itemType": "computerProgram",
        "title": "A library",
        "creators": [
            {"creatorType": "programmer", "firstName": "Ada", "lastName": "Lovelace"},
            {"creatorType": "programmer", "firstName": "Alan", "lastName": "Turing"},
        ],
    }
    assert ("author", "Lovelace, Ada and Turing, Alan") in fields(data)
