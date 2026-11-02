"""PDF retrieval in `ws fetch`: `fetch` driven in-process with fake sources, and each
real source driven with a fake network.
"""

import json
import os
import urllib.error
from pathlib import Path

import pytest
from conftest import Tree
from rkt import inquiry, retrieve
from rkt.fetch import fetch

PDF = b"%PDF-1.7 a paper"

BIBLIOGRAPHY = """% Exported from Zotero with Better BibTeX
@article{raissi2019,
  title = {Physics-informed neural networks},
  doi = {10.1016/j.jcp.2018.10.045},
}

@misc{karniadakis2021,
  title = {Physics-informed machine learning},
  eprint = {2101.00001},
  archiveprefix = {arXiv},
}

@phdthesis{bonnet2025Thesis,
  title = {A thesis},
}
"""


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
def synced(tree: Tree) -> Tree:
    workspace = tree
    (workspace.hub / "references.bib").write_text(BIBLIOGRAPHY)
    return workspace


def run(workspace: Tree, sources):
    return fetch([inquiry.load(workspace.root)], sources)


def test_retrieved_pdf_is_saved_under_its_citekey(synced: Tree) -> None:
    lines, ok = run(synced, [Fake("a", has={"raissi2019"})])

    assert ok
    assert (synced.pool / "papers" / "raissi2019.pdf").read_bytes() == PDF
    assert "papers/raissi2019.pdf" not in lines
    assert "papers/bonnet2025Thesis.pdf" in lines
    assert not list((synced.pool / "papers").glob(".*"))


def test_sources_are_tried_in_order_until_one_has_it(synced: Tree) -> None:
    first, second = Fake("first", has={"raissi2019"}), Fake("second", has=set())

    run(synced, [first, second])

    assert "raissi2019" in first.asked and "raissi2019" not in second.asked
    assert "bonnet2025Thesis" in second.asked


def test_failures_fall_through_to_the_missing_list(synced: Tree) -> None:
    failing = Fake("broken", fails={"raissi2019", "bonnet2025Thesis"})
    fallback = Fake("fallback", has={"karniadakis2021"})

    lines, ok = run(synced, [failing, fallback])

    assert ok
    assert "papers/raissi2019.pdf" in lines
    assert (synced.pool / "papers" / "karniadakis2021.pdf").exists()
    assert any("broken: unreachable" in line for line in lines)


def test_document_already_in_the_pool_is_not_asked_for(synced: Tree) -> None:
    (synced.pool / "papers").mkdir()
    (synced.pool / "papers" / "raissi2019.pdf").write_bytes(b"mine")
    source = Fake("a")

    run(synced, [source])

    assert "raissi2019" not in source.asked


def test_document_listed_twice_is_asked_for_once(synced: Tree) -> None:
    (synced.child / "references.bib").write_text(BIBLIOGRAPHY)
    source = Fake("a")

    lines, _ = fetch(inquiry.tree(inquiry.load(synced.root)), [source])

    assert source.asked.count("raissi2019") == 1
    assert "demo/framework: 3 missing" in lines


def test_bibliography_identifiers_are_read() -> None:
    entries = retrieve.entries(
        BIBLIOGRAPHY
        + "@article{doiArxiv, doi = {10.48550/arXiv.2201.1}\n}\n"
        + "@misc{urlArxiv,\n  url = {https://arxiv.org/abs/2301.2v2},\n}\n"
    )

    assert entries["raissi2019"].doi == "10.1016/j.jcp.2018.10.045"
    assert entries["raissi2019"].arxiv is None
    assert entries["karniadakis2021"].arxiv == "2101.00001"
    assert entries["bonnet2025Thesis"] == retrieve.Entry("bonnet2025Thesis")
    assert entries["urlArxiv"].arxiv == "2301.2v2"


class Network:
    """A fake web: URL prefixes to bodies; records every URL asked."""

    def __init__(self, pages: dict[str, bytes]):
        self.pages = pages
        self.asked: list[str] = []

    def __call__(self, url, headers):
        self.asked.append(url)
        for prefix, body in self.pages.items():
            if url.startswith(prefix):
                return body
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)


def write_config(tmp_path: Path, text: str) -> None:
    config = Path(os.environ["XDG_CONFIG_HOME"]) / "rkt"
    config.mkdir(parents=True)
    (config / "config.yaml").write_text(text)


def test_without_zotero_configuration_no_zotero_call_is_made(tmp_path: Path) -> None:
    web = Network({})
    sources, problems = retrieve.configured(web)

    retrieve.retrieve(retrieve.Entry("x", doi="10.1/x", arxiv="2101.1"), sources)

    assert problems == []
    assert not any("zotero" in url for url in web.asked)
    assert [source.name for source in sources] == ["arXiv"]


def test_configured_order_is_zotero_arxiv_unpaywall(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        "zotero:\n  library: users/1\n  api_key: k\nemail: me@example.org\n",
    )
    web = Network({})
    sources, problems = retrieve.configured(web)

    retrieve.retrieve(retrieve.Entry("x", doi="10.1/x", arxiv="2101.1"), sources)

    assert problems == []
    assert [source.name for source in sources] == ["Zotero", "arXiv", "Unpaywall"]
    hosts = [url.split("/")[2] for url in web.asked]
    assert hosts == ["api.zotero.org", "arxiv.org", "api.unpaywall.org"]


def test_zotero_finds_the_attachment_of_the_item_with_the_citekey() -> None:
    base = "https://api.zotero.org/users/1/items"
    web = Network(
        {
            f"{base}?q=": json.dumps(
                [
                    {"key": "OTHER", "data": {"citationKey": "raissi2019b"}},
                    {"key": "ITEM", "data": {"extra": "Citation Key: raissi2019"}},
                ]
            ).encode(),
            f"{base}/ITEM/children": json.dumps(
                [{"key": "ATT", "data": {"contentType": "application/pdf"}}]
            ).encode(),
            f"{base}/ATT/file": PDF,
        }
    )

    pdf = retrieve.Zotero("users/1", "k", web).retrieve(retrieve.Entry("raissi2019"))

    assert pdf == PDF
    assert not any("OTHER" in url for url in web.asked)


def test_unpaywall_downloads_the_open_access_pdf() -> None:
    web = Network(
        {
            "https://api.unpaywall.org/v2/10.1/x": json.dumps(
                {"best_oa_location": {"url_for_pdf": "https://oa.example/x.pdf"}}
            ).encode(),
            "https://oa.example/x.pdf": PDF,
        }
    )

    pdf = retrieve.Unpaywall("me@example.org", web).retrieve(
        retrieve.Entry("x", doi="10.1/x")
    )

    assert pdf == PDF


def test_a_page_that_is_not_a_pdf_is_not_kept() -> None:
    web = Network({"https://arxiv.org/pdf/2101.1": b"<html>captcha</html>"})

    assert retrieve.Arxiv(web).retrieve(retrieve.Entry("x", arxiv="2101.1")) is None


def test_network_error_is_a_retrieval_error() -> None:
    def down(url, headers):
        raise OSError("no route")

    with pytest.raises(retrieve.RetrievalError):
        retrieve.Arxiv(down).retrieve(retrieve.Entry("x", arxiv="2101.1"))


def test_unpaywall_tries_the_next_copy_when_one_is_refused() -> None:
    pages = {
        "https://api.unpaywall.org/v2/10.1/x": json.dumps(
            {
                "best_oa_location": {"url_for_pdf": "https://refused.example/x.pdf"},
                "oa_locations": [{"url_for_pdf": "https://oa.example/x.pdf"}],
            }
        ).encode(),
        "https://oa.example/x.pdf": PDF,
    }

    def get(url, headers):
        if "refused" in url:
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        return Network(pages)(url, headers)

    pdf = retrieve.Unpaywall("me@example.org", get).retrieve(
        retrieve.Entry("x", doi="10.1/x")
    )

    assert pdf == PDF


def test_pdf_folder_is_tried_first(tmp_path: Path) -> None:
    folder = tmp_path / "OneDrive" / "Zotero"
    folder.mkdir(parents=True)
    write_config(
        tmp_path,
        f"pdf_folder: {folder}\nzotero:\n  library: users/1\n  api_key: k\n",
    )
    sources, problems = retrieve.configured(Network({}))

    assert problems == []
    assert [source.name for source in sources] == ["PDF folder", "Zotero", "arXiv"]


def test_pdf_folder_gives_the_file_named_by_the_citekey(tmp_path: Path) -> None:
    (tmp_path / "raissi2019.pdf").write_bytes(PDF)
    (tmp_path / "notes.pdf").write_bytes(b"<html>not a pdf</html>")
    folder = retrieve.Folder(tmp_path)

    assert folder.retrieve(retrieve.Entry("raissi2019")) == PDF
    assert folder.retrieve(retrieve.Entry("other2020")) is None
    assert folder.retrieve(retrieve.Entry("notes")) is None


def test_a_missing_pdf_folder_is_a_problem_not_a_source(tmp_path: Path) -> None:
    write_config(tmp_path, f"pdf_folder: {tmp_path / 'nowhere'}\n")

    sources, problems = retrieve.configured(Network({}))

    assert [source.name for source in sources] == ["arXiv"]
    assert problems and "nowhere" in problems[0]


class LocalApi:
    """Zotero's local API for one item with a PDF attachment, as `get` sees it."""

    def __init__(self, attachment: dict) -> None:
        self.attachment = attachment

    def __call__(self, url: str, headers: dict) -> bytes:
        if "/children" in url:
            return json.dumps([self.attachment]).encode()
        return json.dumps(
            [{"key": "ITEM", "data": {"citationKey": "raissi2019"}},
             {"key": "OTHER", "data": {"citationKey": "someone2020"}}]
        ).encode()


def pdf_attachment(**data: str) -> dict:
    return {"key": "ATT1", "data": {"contentType": "application/pdf", **data}}


def test_local_zotero_reads_a_zotmoov_linked_file(tmp_path: Path) -> None:
    moved = tmp_path / "ZotMoov" / "Raissi et al. - 2019 - PINNs.pdf"
    moved.parent.mkdir()
    moved.write_bytes(PDF)
    api = LocalApi(pdf_attachment(linkMode="linked_file", path=str(moved)))

    body = retrieve.ZoteroLocal(get=api).retrieve(retrieve.Entry("raissi2019"))

    assert body == PDF


def test_local_zotero_resolves_the_linked_attachment_base_folder(tmp_path: Path) -> None:
    (tmp_path / "papers").mkdir()
    (tmp_path / "papers" / "raissi.pdf").write_bytes(PDF)
    api = LocalApi(pdf_attachment(linkMode="linked_file", path="attachments:papers/raissi.pdf"))

    source = retrieve.ZoteroLocal(base=tmp_path, get=api)

    assert source.retrieve(retrieve.Entry("raissi2019")) == PDF
    assert retrieve.ZoteroLocal(get=api).retrieve(retrieve.Entry("raissi2019")) is None


def test_local_zotero_reads_a_stored_file(tmp_path: Path) -> None:
    (tmp_path / "ATT1").mkdir()
    (tmp_path / "ATT1" / "raissi.pdf").write_bytes(PDF)
    api = LocalApi(pdf_attachment(linkMode="imported_file", filename="raissi.pdf"))

    body = retrieve.ZoteroLocal(storage=tmp_path, get=api).retrieve(retrieve.Entry("raissi2019"))

    assert body == PDF


def test_local_zotero_not_running_falls_through(tmp_path: Path) -> None:
    def refused(url: str, headers: dict) -> bytes:
        raise OSError("connection refused")

    with pytest.raises(retrieve.RetrievalError):
        retrieve.ZoteroLocal(get=refused).retrieve(retrieve.Entry("raissi2019"))


def test_a_windows_path_is_read_under_mnt_from_wsl() -> None:
    if os.name == "nt":
        pytest.skip("only under WSL or Linux")
    assert retrieve.local_path(r"D:\Zotero\ZotMoov\a b.pdf") == Path("/mnt/d/Zotero/ZotMoov/a b.pdf")


def test_local_zotero_is_configured_before_the_web_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config" / "rkt" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "zotero_local: true\nzotero_base: ~/ZotMoov\n"
        "zotero:\n  library: users/1\n  api_key: k\n"
    )

    sources, problems = retrieve.configured()

    assert problems == []
    assert [source.name for source in sources] == ["Zotero (local)", "Zotero", "arXiv"]
    assert sources[0].base == Path("~/ZotMoov")


def test_web_zotero_reads_a_linked_file_from_a_synced_folder(tmp_path: Path) -> None:
    # The laptop recorded a portable path under its linked attachment base folder; the
    # workstation has no Zotero app, only the folder synced over a drive.
    synced = tmp_path / "OneDrive" / "ZotMoov"
    synced.mkdir(parents=True)
    (synced / "Raissi - 2019.pdf").write_bytes(PDF)
    api = LocalApi(pdf_attachment(linkMode="linked_file", path="attachments:Raissi - 2019.pdf"))

    source = retrieve.Zotero("users/1", "key", api, base=synced)

    assert source.retrieve(retrieve.Entry("raissi2019")) == PDF


def test_web_zotero_finds_a_linked_file_recorded_on_another_machine(tmp_path: Path) -> None:
    synced = tmp_path / "ZotMoov"
    (synced / "PINNs").mkdir(parents=True)
    (synced / "PINNs" / "Raissi - 2019.pdf").write_bytes(PDF)
    recorded = r"C:\Users\me\OneDrive\ZotMoov\PINNs\Raissi - 2019.pdf"
    api = LocalApi(pdf_attachment(linkMode="linked_file", path=recorded))

    found = retrieve.Zotero("users/1", "key", api, base=synced)
    without = retrieve.Zotero("users/1", "key", api)

    assert found.retrieve(retrieve.Entry("raissi2019")) == PDF
    assert without.retrieve(retrieve.Entry("raissi2019")) is None


def test_the_synced_folder_serves_the_web_api_too(tmp_path: Path) -> None:
    config = tmp_path / "config" / "rkt" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("zotero_base: ~/ZotMoov\nzotero:\n  library: users/1\n  api_key: k\n")

    sources, _ = retrieve.configured()

    assert [source.name for source in sources] == ["Zotero", "arXiv"]
    assert sources[0].base == Path("~/ZotMoov").expanduser()
