"""PDF retrieval for `fetch`: each source driven with a fake network."""

import json
import os
import urllib.error
from pathlib import Path

import pytest
from fetch import manifest, retrieve
from test_fetch import BIBLIOGRAPHY, PDF


def test_bibliography_identifiers_are_read() -> None:
    entries = manifest.entries(
        BIBLIOGRAPHY
        + "@article{doiArxiv, doi = {10.48550/arXiv.2201.1}\n}\n"
        + "@misc{urlArxiv,\n  url = {https://arxiv.org/abs/2301.2v2},\n}\n"
    )

    assert entries["raissi2019"].doi == "10.1016/j.jcp.2018.10.045"
    assert entries["raissi2019"].arxiv is None
    assert entries["karniadakis2021"].arxiv == "2101.00001"
    assert entries["doe2025Thesis"] == manifest.Entry("doe2025Thesis")
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
    config = Path(os.environ["XDG_CONFIG_HOME"]) / "research-agent"
    config.mkdir(parents=True)
    (config / "retrieval.yaml").write_text(text)


def test_without_zotero_configuration_no_zotero_call_is_made(tmp_path: Path) -> None:
    web = Network({})
    sources, problems = retrieve.configured(web)

    retrieve.retrieve(manifest.Entry("x", doi="10.1/x", arxiv="2101.1"), sources)

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

    retrieve.retrieve(manifest.Entry("x", doi="10.1/x", arxiv="2101.1"), sources)

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

    pdf = retrieve.Zotero("users/1", "k", web).retrieve(manifest.Entry("raissi2019"))

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
        manifest.Entry("x", doi="10.1/x")
    )

    assert pdf == PDF


def test_a_page_that_is_not_a_pdf_is_not_kept() -> None:
    web = Network({"https://arxiv.org/pdf/2101.1": b"<html>captcha</html>"})

    assert retrieve.Arxiv(web).retrieve(manifest.Entry("x", arxiv="2101.1")) is None


def test_network_error_is_a_retrieval_error() -> None:
    def down(url, headers):
        raise OSError("no route")

    with pytest.raises(retrieve.RetrievalError):
        retrieve.Arxiv(down).retrieve(manifest.Entry("x", arxiv="2101.1"))


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
        manifest.Entry("x", doi="10.1/x")
    )

    assert pdf == PDF
