"""`ws refs`: the bibliography pulled from Zotero, and references added to it.

Driven in-process against a fake web (see `fakes`); the command line itself is run
only where no request goes out.
"""

import pytest
from conftest import Workspace
from fakes import Web
from ws import lookup, manifest, refs, retrieve, zotero
from ws.fetch import fetch

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


@pytest.fixture
def synced(workspace: Workspace) -> Workspace:
    result = workspace.sync()
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace


@pytest.fixture
def web() -> Web:
    """A library with the collection of each repository under `demo`."""
    web = Web()
    demo = web.collection("demo")
    web.hub = web.collection("demo-hub", demo)
    web.framework = web.collection("demo-framework", demo)
    return web


def pull(workspace: Workspace, web: Web, name: str = "demo-hub"):
    return refs.pull(workspace.root, manifest.load(workspace.hub), name, web.library())


def test_pull_writes_the_collection_in_the_fixed_form(
    synced: Workspace, web: Web
) -> None:
    web.item([web.hub], **RAISSI)

    lines, ok = pull(synced, web)

    assert ok, lines
    assert (synced.hub / "references.bib").read_text() == (
        "% Written by `ws refs pull` from the Zotero collection demo/demo-hub.\n"
        "% Add a reference with `ws refs add`, never here.\n"
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


def test_entries_are_sorted_and_carry_what_fetch_reads(
    synced: Workspace, web: Web
) -> None:
    web.item([web.hub], **RAISSI)
    web.item([web.hub], **KARNIADAKIS)
    web.item([web.framework], **{**RAISSI, "citationKey": "elsewhere2020"})

    pull(synced, web)

    text = (synced.hub / "references.bib").read_text()
    found = retrieve.entries(text)
    assert list(found) == ["karniadakis2021physics", "raissi2019physics"]
    assert found["karniadakis2021physics"].arxiv == "2101.00001"
    assert found["raissi2019physics"].doi == "10.1016/j.jcp.2018.10.045"
    assert "@misc{karniadakis2021physics," in text
    assert "  eprint = {2101.00001},\n  archiveprefix = {arXiv},\n" in text


def test_entry_gone_from_the_collection_is_removed_and_a_cited_one_warned(
    synced: Workspace, web: Web
) -> None:
    web.item([web.hub], **RAISSI)
    (synced.hub / "references.bib").write_text(
        "@article{raissi2019physics,\n}\n"
        "@article{forgotten2010,\n}\n"
        "@article{cited-one2011,\n}\n"
    )
    (synced.hub / "docs" / "wiki").mkdir(parents=True, exist_ok=True)
    (synced.hub / "docs" / "wiki" / "note.md").write_text(
        "As shown [@raissi2019physics; @cited-one2011, p. 3].\n"
        "Not a citation: @forgotten2010s.\n"
    )

    lines, ok = pull(synced, web)

    assert ok, lines
    assert list(retrieve.entries((synced.hub / "references.bib").read_text())) == [
        "raissi2019physics"
    ]
    assert "demo-hub: references.bib: removed cited-one2011, forgotten2010" in lines
    assert (
        "demo-hub: WARNING: cited-one2011 is no longer in the collection, "
        "but docs/wiki/note.md cites it"
    ) in lines
    assert not any("WARNING: forgotten2010" in line for line in lines)


def test_citekey_pinned_in_extra_is_kept(synced: Workspace, web: Web) -> None:
    item = {key: value for key, value in RAISSI.items() if key != "citationKey"}
    web.item([web.hub], **item, extra="tex.ids: other\nCitation Key: raissiPINN2019")

    pull(synced, web)

    assert "@article{raissiPINN2019," in (synced.hub / "references.bib").read_text()


def without_citekey(item: dict) -> dict:
    return {key: value for key, value in item.items() if key != "citationKey"}


def test_item_without_citekey_gets_one_unique_in_the_library_and_written_back(
    synced: Workspace, web: Web
) -> None:
    web.item([web.framework], **RAISSI)
    new = web.item(
        [web.hub],
        **{
            **without_citekey(RAISSI),
            "title": "The physics of networks",
            "creators": [
                {"creatorType": "author", "firstName": "Anna", "lastName": "Raissi"},
                {"creatorType": "author", "firstName": "B", "lastName": "Other"},
            ],
        },
    )
    thesis = web.item(
        [web.hub],
        itemType="thesis",
        title="Physics-Informed Neural Networks for Material Modeling",
        creators=[
            {
                "creatorType": "author",
                "firstName": "Damien",
                "lastName": "Bonnet-Eymard",
            }
        ],
        date="2026",
        university="KU Leuven",
    )

    lines, ok = pull(synced, web)

    assert ok, lines
    assert web.data(new)["citationKey"] == "raissi2019physicsa"
    assert web.data(thesis)["citationKey"] == "bonnet-eymard2026physics"
    found = retrieve.entries((synced.hub / "references.bib").read_text())
    assert list(found) == ["bonnet-eymard2026physics", "raissi2019physicsa"]


def test_read_only_key_pulls_but_fails_the_write_back(
    synced: Workspace, web: Web
) -> None:
    web.writable = False
    item = web.item([web.hub], **without_citekey(RAISSI))

    lines, ok = pull(synced, web)

    assert not ok
    assert "citationKey" not in web.data(item)
    assert "@article{raissi2019physics," in (synced.hub / "references.bib").read_text()
    assert any(
        line.startswith("demo-hub: FAILED: the Zotero key is read-only")
        for line in lines
    ), lines


def test_manifest_can_name_the_collection_by_key(synced: Workspace, web: Web) -> None:
    elsewhere = web.collection("My old PINN papers")
    web.item([elsewhere], **RAISSI)
    manifest_path = synced.hub / "workspace.yaml"
    manifest_path.write_text(
        manifest_path.read_text().replace(
            "    role: hub\n", f"    role: hub\n    zotero_collection: {elsewhere}\n"
        )
    )

    lines, ok = pull(synced, web)

    assert ok, lines
    text = (synced.hub / "references.bib").read_text()
    assert f"from the Zotero collection {elsewhere}." in text
    assert "@article{raissi2019physics," in text


def test_pull_without_configuration_names_the_repository_it_is_run_from(
    synced: Workspace,
) -> None:
    study = synced.root / "demo-framework"
    (study / "references.bib").write_text("@article{kept2020,\n}\n")
    (study / "docs").mkdir(exist_ok=True)

    result = synced.run_in(study / "docs", "refs", "pull")

    assert result.returncode == 1
    assert (
        "demo-framework: FAILED: no Zotero configuration in "
        f"{synced.tmp / 'config' / 'research-ws' / 'retrieval.yaml'}"
    ) in result.stdout
    assert (study / "references.bib").read_text() == "@article{kept2020,\n}\n"


def test_pull_from_outside_any_repository_asks_for_one(synced: Workspace) -> None:
    result = synced.run_in(synced.root, "refs", "pull")

    assert result.returncode == 2
    assert "give --repo" in result.stderr


def test_pull_names_a_repository_with_repo(synced: Workspace) -> None:
    result = synced.run("refs", "pull", "--repo", "demo-framework")

    assert "demo-framework: FAILED: no Zotero configuration" in result.stdout


def test_fetch_pulls_every_repository_before_retrieving(
    synced: Workspace, web: Web
) -> None:
    web.item([web.hub], **RAISSI)
    web.item([web.framework], **KARNIADAKIS)

    lines, ok = fetch(synced.root, manifest.load(synced.hub), [], web.library())

    assert ok, lines
    assert "raissi2019physics" in (synced.hub / "references.bib").read_text()
    framework = synced.root / "demo-framework" / "references.bib"
    assert "karniadakis2021physics" in framework.read_text()
    assert (
        "demo: no Zotero collection demo/demo, references.bib left as it is"
        in lines
    )
    # What the pull wrote is what is retrieved.
    assert "papers/raissi2019physics.pdf" in lines


def test_fetch_with_zotero_unreachable_skips_the_pull(
    synced: Workspace, web: Web
) -> None:
    web.down = True
    (synced.hub / "references.bib").write_text("@article{kept2020,\n}\n")

    lines, ok = fetch(synced.root, manifest.load(synced.hub), [], web.library())

    assert ok, lines
    assert [line for line in lines if line.startswith("zotero:")] == [
        "zotero: skipped (Zotero is unreachable: no route to host)"
    ]
    assert (synced.hub / "references.bib").read_text() == "@article{kept2020,\n}\n"
    assert "papers/kept2020.pdf" in lines


def test_fetch_without_configuration_skips_the_pull(synced: Workspace) -> None:
    (synced.hub / "references.bib").write_text("@article{kept2020,\n}\n")

    result = synced.fetch()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("zotero: skipped (no Zotero configuration in ")
    assert (synced.hub / "references.bib").read_text() == "@article{kept2020,\n}\n"


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


def add(workspace: Workspace, web: Web, identifier: str, name: str = "demo-hub"):
    return refs.add(
        workspace.root,
        manifest.load(workspace.hub),
        name,
        lookup.identify(identifier),
        web.library(),
    )


def test_add_creates_the_item_from_crossref_in_the_collection_and_pulls(
    synced: Workspace, web: Web
) -> None:
    web.crossref["10.1016/j.jcp.2018.10.045"] = CROSSREF_RAISSI

    lines, ok = add(synced, web, "10.1016/J.JCP.2018.10.045")

    assert ok, lines
    [item] = web.items.values()
    data = item["data"]
    assert data["itemType"] == "journalArticle"
    assert data["collections"] == [web.hub]
    assert data["citationKey"] == "raissi2019physics"
    assert data["publicationTitle"] == "Journal of Computational Physics"
    assert data["creators"][1] == {
        "creatorType": "author",
        "firstName": "G.E.",
        "lastName": "Karniadakis",
    }
    assert data["abstractNote"] == "We introduce physics-informed neural networks."
    assert lines[0] == "demo-hub: added raissi2019physics"
    assert "run `uv run ws fetch` in the hub to retrieve its PDF" in lines[-1]
    text = (synced.hub / "references.bib").read_text()
    assert (
        retrieve.entries(text)["raissi2019physics"].doi == "10.1016/j.jcp.2018.10.045"
    )
    assert "  month = {feb},\n" in text


def test_add_asks_datacite_for_a_doi_crossref_does_not_know(
    synced: Workspace, web: Web
) -> None:
    web.datacite["10.5281/zenodo.123"] = {
        "doi": "10.5281/zenodo.123",
        "titles": [{"title": "SPINN benchmark fields"}],
        "creators": [
            {"name": "Doe, Jane", "givenName": "Jane", "familyName": "Doe"},
            {"name": "KU Leuven", "nameType": "Organizational"},
        ],
        "publisher": "Zenodo",
        "publicationYear": 2024,
        "types": {"resourceTypeGeneral": "Dataset"},
        "descriptions": [
            {"description": "<p>Fields.</p>", "descriptionType": "Abstract"}
        ],
        "url": "https://zenodo.org/records/123",
    }

    lines, ok = add(synced, web, "https://doi.org/10.5281/zenodo.123")

    assert ok, lines
    [item] = web.items.values()
    assert item["data"]["itemType"] == "dataset"
    assert item["data"]["citationKey"] == "doe2024spinn"
    assert item["data"]["creators"][1] == {"creatorType": "author", "name": "KU Leuven"}
    assert item["data"]["abstractNote"] == "Fields."
    assert (
        retrieve.entries((synced.hub / "references.bib").read_text())[
            "doe2024spinn"
        ].doi
        == "10.5281/zenodo.123"
    )


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
    synced: Workspace, web: Web, identifier: str
) -> None:
    web.arxiv["2101.00001"] = {
        "title": "Physics-informed\n  machine learning",
        "summary": "  Physics meets data.\n",
        "authors": ["George Em Karniadakis", "Ioannis G. Kevrekidis"],
        "published": "2021-01-04T18:00:00Z",
    }

    lines, ok = add(synced, web, identifier)

    assert ok, lines
    [item] = web.items.values()
    data = item["data"]
    assert data["itemType"] == "preprint"
    assert data["title"] == "Physics-informed machine learning"
    assert data["archiveID"] == "arXiv:2101.00001"
    assert data["creators"][0] == {
        "creatorType": "author",
        "firstName": "George Em",
        "lastName": "Karniadakis",
    }
    assert data["citationKey"] == "karniadakis2021physics"
    entry = retrieve.entries((synced.hub / "references.bib").read_text())[
        "karniadakis2021physics"
    ]
    assert entry.arxiv == "2101.00001"


@pytest.mark.parametrize(
    "item, identifier",
    [
        (RAISSI, "https://doi.org/10.1016/J.JCP.2018.10.045"),
        (KARNIADAKIS, "arXiv:2101.00001v1"),
        ({**KARNIADAKIS, "archiveID": "", "DOI": ""}, "2101.00001"),
    ],
)
def test_add_reuses_the_item_already_in_the_library(
    synced: Workspace, web: Web, item: dict, identifier: str
) -> None:
    web.item(
        [web.framework],
        **{
            **RAISSI,
            "title": "Decoy",
            "citationKey": "decoy",
            "DOI": "10.1016/j.jcp.2018.10.0451",
        },
    )
    existing = web.item([web.framework], **item)

    lines, ok = add(synced, web, identifier)

    assert ok, lines
    assert len(web.items) == 2
    assert web.data(existing)["collections"] == [web.framework, web.hub]
    key = item["citationKey"]
    assert lines[0] == f"demo-hub: added {key}, already in Zotero"
    assert key in retrieve.entries((synced.hub / "references.bib").read_text())
    assert not any(
        "crossref" in url or "arxiv.org/api" in url for _, url in web.requests
    )


def test_add_finds_the_item_by_its_title_when_zotero_misses_the_doi(
    synced: Workspace, web: Web
) -> None:
    # Zotero's search seldom finds a DOI whole; the item is then found by its title.
    web.finds_whole_dois = False
    web.crossref["10.1016/j.jcp.2018.10.045"] = CROSSREF_RAISSI
    existing = web.item([web.framework], **RAISSI)

    lines, ok = add(synced, web, "10.1016/j.jcp.2018.10.045")

    assert ok, lines
    assert len(web.items) == 1
    assert web.data(existing)["collections"] == [web.framework, web.hub]
    assert lines[0] == f"demo-hub: added {RAISSI['citationKey']}, already in Zotero"


@pytest.mark.parametrize(
    "identifier", ["https://example.org/thesis.pdf", "Raissi et al. 2019", "hdl:1234/5"]
)
def test_add_refuses_anything_but_a_doi_or_arxiv_identifier(
    synced: Workspace, identifier: str
) -> None:
    result = synced.run("refs", "add", identifier)

    assert result.returncode == 1
    assert "demo-hub: FAILED: " in result.stdout
    assert "add a thesis, report or slides by hand in Zotero" in result.stdout


def test_add_without_configuration_says_so(synced: Workspace) -> None:
    result = synced.run("refs", "add", "10.1000/x", "--repo", "demo-framework")

    assert result.returncode == 1
    assert "demo-framework: FAILED: no Zotero configuration" in result.stdout


def test_add_with_a_read_only_key_fails_with_a_clear_message(
    synced: Workspace, web: Web
) -> None:
    web.crossref["10.1016/j.jcp.2018.10.045"] = CROSSREF_RAISSI
    web.writable = False

    with pytest.raises(zotero.ReadOnly, match="the Zotero key is read-only"):
        add(synced, web, "10.1016/j.jcp.2018.10.045")

    assert web.items == {}


PDF = b"%PDF-1.7 a paper"


class Arxiv:
    """A source that has every PDF."""

    name = "arXiv"

    def retrieve(self, entry):
        return PDF


def test_fetch_attaches_a_retrieved_pdf_to_its_item_when_asked(
    synced: Workspace, web: Web
) -> None:
    item = web.item([web.hub], **RAISSI)

    lines, ok = fetch(
        synced.root, manifest.load(synced.hub), [Arxiv()], web.library(upload_pdfs=True)
    )

    assert ok, lines
    [attachment] = [
        key
        for key, value in web.items.items()
        if value["data"].get("parentItem") == item
    ]
    assert web.data(attachment)["contentType"] == "application/pdf"
    assert web.data(attachment)["filename"] == "raissi2019physics.pdf"
    assert web.files[attachment] == PDF
    assert (
        "demo-hub: papers/raissi2019physics.pdf retrieved, attached in Zotero"
        in lines
    )


def test_upload_is_off_by_default(synced: Workspace, web: Web) -> None:
    web.item([web.hub], **RAISSI)

    fetch(synced.root, manifest.load(synced.hub), [Arxiv()], web.library())

    assert len(web.items) == 1


def test_a_full_zotero_storage_is_a_warning(synced: Workspace, web: Web) -> None:
    web.item([web.hub], **RAISSI)
    web.quota_full = True

    lines, ok = fetch(
        synced.root, manifest.load(synced.hub), [Arxiv()], web.library(upload_pdfs=True)
    )

    assert ok, lines
    assert (synced.pool / "papers" / "raissi2019physics.pdf").read_bytes() == PDF
    assert (
        "demo-hub: WARNING: papers/raissi2019physics.pdf not attached in Zotero: "
        "its file storage is full"
    ) in lines
    # The attachment made for it is not left empty in the library.
    assert len(web.items) == 1


def test_software_programmers_are_its_authors():
    from ws.bibtex import fields

    data = {
        "itemType": "computerProgram",
        "title": "jaxmat",
        "creators": [
            {"creatorType": "programmer", "firstName": "Jeremy", "lastName": "Bleyer"},
            {"creatorType": "programmer", "firstName": "Jack S.", "lastName": "Hale"},
        ],
    }
    assert ("author", "Bleyer, Jeremy and Hale, Jack S.") in fields(data)
