"""A fake web for `rkt refs`: the Zotero Web API of one library, Crossref, DataCite and arXiv.

Each is answered from memory, as `ws` sends its requests (method, URL, headers, body);
nothing goes to the network.
"""

import json
import urllib.parse
from pathlib import Path

from rkt import zotero

LIBRARY = "users/1"
KEY = "secret"
# The fields of each item type, from the Zotero schema (`https://api.zotero.org/schema`).
SCHEMA = json.loads((Path(__file__).with_name("zotero-fields.json")).read_text())
# What every item has besides its type's fields.
_COMMON = {"itemType", "creators", "tags", "collections", "relations", "key", "version"}
_ATTACHMENT = {
    "parentItem",
    "linkMode",
    "contentType",
    "charset",
    "filename",
    "md5",
    "mtime",
    "title",
    "note",
    "url",
    "accessDate",
}


def _valid(data: dict) -> str | None:
    """Why the Web API would refuse `data` as an item, or None."""
    kind = data.get("itemType")
    if kind == "attachment":
        allowed = _COMMON | _ATTACHMENT
    elif kind in SCHEMA["itemTypes"]:
        allowed = _COMMON | set(SCHEMA["itemTypes"][kind])
    else:
        return f"'{kind}' is not a valid itemType"
    unknown = sorted(set(data) - allowed)
    return f"'{unknown[0]}' is not a valid field for type '{kind}'" if unknown else None


class Web:
    """The web `ws` sees: a Zotero library and the metadata services, all in memory."""

    def __init__(self) -> None:
        self.collections: dict[str, dict] = {}
        self.items: dict[str, dict] = {}
        self.files: dict[str, bytes] = {}
        self.crossref: dict[str, dict] = {}
        self.datacite: dict[str, dict] = {}
        self.arxiv: dict[str, str] = {}
        self.writable = True
        self.quota_full = False
        self.down = False
        # The Web API's search splits a DOI into words; with this off, it never finds one.
        self.finds_whole_dois = True
        self.requests: list[tuple[str, str]] = []
        # File uploads authorized, by upload URL path, then uploaded, by upload key.
        self.uploads: dict[str, dict] = {}
        self.uploaded: dict[str, dict] = {}
        self._next = 0
        # As in Zotero, every write moves the library's version, which the objects it
        # wrote take.
        self.version = 100

    # The library's content, as a test sets it up.

    def _key(self) -> str:
        self._next += 1
        return f"K{self._next:07d}"

    def collection(self, name: str, parent: str | None = None) -> str:
        key = self._key()
        self.collections[key] = {
            "key": key,
            "version": 1,
            "data": {"key": key, "name": name, "parentCollection": parent or False},
        }
        return key

    def item(self, collections: list[str] = (), **data) -> str:
        assert _valid(data) is None, _valid(data)
        key = self._key()
        self.items[key] = {
            "key": key,
            "version": 1,
            "data": {
                "key": key,
                "version": 1,
                "collections": list(collections),
                **data,
            },
        }
        return key

    def data(self, key: str) -> dict:
        return self.items[key]["data"]

    def library(self, upload_pdfs: bool = False) -> zotero.Library:
        return zotero.Library(LIBRARY, KEY, self, upload_pdfs)

    # The web, as `ws` asks it.

    def __call__(self, method, url, headers, body=None) -> zotero.Response:
        self.requests.append((method, url))
        if self.down:
            raise OSError("no route to host")
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query))
        if parts.netloc == "api.crossref.org":
            doi = urllib.parse.unquote(parts.path.removeprefix("/works/")).lower()
            if doi not in self.crossref:
                return _reply(404, "Resource not found.")
            return _reply(200, {"status": "ok", "message": self.crossref[doi]})
        if parts.netloc == "api.datacite.org":
            doi = urllib.parse.unquote(parts.path.removeprefix("/dois/")).lower()
            if doi not in self.datacite:
                return _reply(404, {"errors": [{"status": "404"}]})
            return _reply(200, {"data": {"id": doi, "attributes": self.datacite[doi]}})
        if parts.netloc == "export.arxiv.org":
            return _reply(200, self._atom(query.get("id_list", "")))
        if parts.netloc == "uploads.zotero.example":
            upload = self.uploads.pop(parts.path.strip("/"))
            assert headers.get("Content-Type") == upload["contentType"]
            assert body.startswith(upload["prefix"].encode())
            assert body.endswith(upload["suffix"].encode())
            upload["file"] = body[
                len(upload["prefix"]) : len(body) - len(upload["suffix"])
            ]
            self.uploaded[upload["uploadKey"]] = upload
            return _reply(201)
        if parts.netloc == "api.zotero.org":
            assert headers.get("Zotero-API-Key") == KEY
            path = parts.path.removeprefix(f"/{LIBRARY}/")
            return self._zotero(method, path, query, headers, body)
        raise AssertionError(f"unexpected request: {method} {url}")

    def _atom(self, identifier: str) -> str:
        """The arXiv API's Atom feed for one identifier: empty if it does not know it."""
        entries = ""
        if identifier in self.arxiv:
            paper = self.arxiv[identifier]
            authors = "".join(
                f"<author><name>{name}</name></author>" for name in paper["authors"]
            )
            entries = (
                f"<entry><id>http://arxiv.org/abs/{identifier}v2</id>"
                f"<published>{paper['published']}</published>"
                f"<title>{paper['title']}</title><summary>{paper['summary']}</summary>"
                f'{authors}<arxiv:primary_category term="cs.LG"/></entry>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:arxiv="http://arxiv.org/schemas/atom">'
            f"<title>arXiv Query</title>{entries}</feed>"
        )

    def _zotero(self, method, path, query, headers, body) -> zotero.Response:
        segments = path.split("/")
        if method != "GET" and not self.writable:
            return _reply(403, "Write access denied")
        if method == "POST" and segments == ["collections"]:
            successful = {}
            for index, data in enumerate(json.loads(body)):
                key = self.collection(
                    data["name"], data.get("parentCollection") or None
                )
                self.collections[key]["version"] = self._write()
                successful[str(index)] = self.collections[key]
            return _reply(
                200,
                {
                    "successful": successful,
                    "success": {i: o["key"] for i, o in successful.items()},
                    "unchanged": {},
                    "failed": {},
                },
            )
        if method == "GET" and segments == ["collections"]:
            return _page(list(self.collections.values()), query)
        if (
            method == "GET"
            and segments[0] == "collections"
            and segments[2:]
            == [
                "items",
                "top",
            ]
        ):
            members = [
                item
                for item in self.items.values()
                if segments[1] in item["data"]["collections"]
                and "parentItem" not in item["data"]
            ]
            return _page(members, query)
        if method == "GET" and segments in (["items"], ["items", "top"]):
            # Like the Web API's `qmode=everything`: the text anywhere in the item.
            text = query.get("q", "").lower()
            if not self.finds_whole_dois and text.startswith("10."):
                return _page([], query)
            found = [
                item
                for item in self.items.values()
                if text in json.dumps(item["data"]).lower()
                and (segments == ["items"] or "parentItem" not in item["data"])
            ]
            return _page(found, query)
        if method == "PATCH" and segments[0] == "items" and len(segments) == 2:
            item = self.items[segments[1]]
            if headers.get("If-Unmodified-Since-Version") != str(item["version"]):
                return _reply(412, "Item has been modified")
            changes = json.loads(body)
            if problem := _valid({**item["data"], **changes}):
                return _reply(400, problem)
            for name, value in changes.items():
                old = item["data"].get(name)
                # `ws` only ever adds: a value already set is never replaced.
                assert old in (None, "", []) or (
                    isinstance(old, list) and set(old) <= set(value)
                ), f"{name} of {segments[1]} overwritten"
            item["data"].update(changes)
            item["version"] = item["data"]["version"] = self._write()
            return _reply(204, headers={"Last-Modified-Version": str(self.version)})
        if method == "POST" and segments == ["items"]:
            assert headers.get("Content-Type") == "application/json"
            successful, failed = {}, {}
            for index, data in enumerate(json.loads(body)):
                if problem := _valid(data):
                    failed[str(index)] = {"code": 400, "message": problem}
                    continue
                key = self._key()
                version = self._write()
                self.items[key] = {
                    "key": key,
                    "version": version,
                    "data": {**data, "key": key, "version": version},
                }
                successful[str(index)] = self.items[key]
            return _reply(
                200,
                {
                    "successful": successful,
                    "success": {i: o["key"] for i, o in successful.items()},
                    "unchanged": {},
                    "failed": failed,
                },
                {"Last-Modified-Version": str(self.version)},
            )
        if method == "POST" and segments[0] == "items" and segments[2:] == ["file"]:
            return self._file(segments[1], headers, body)
        if method == "DELETE" and segments[0] == "items" and len(segments) == 2:
            item = self.items[segments[1]]
            if headers.get("If-Unmodified-Since-Version") != str(item["version"]):
                return _reply(412, "Item has been modified")
            del self.items[segments[1]]
            self._write()
            return _reply(204)
        raise AssertionError(f"unexpected Zotero request: {method} {path}")

    def _file(self, key: str, headers: dict, body: bytes) -> zotero.Response:
        """The two steps of an attachment's upload around the upload itself: its
        authorization, then its registration.
        """
        assert self.items[key]["data"]["itemType"] == "attachment"
        assert headers.get("Content-Type") == "application/x-www-form-urlencoded"
        assert headers.get("If-None-Match") == "*"
        form = dict(urllib.parse.parse_qsl(body.decode()))
        if "upload" in form:
            upload = self.uploaded.pop(form["upload"])
            self.files[key] = upload["file"]
            assert len(upload["file"]) == int(upload["filesize"])
            return _reply(204)
        if self.quota_full:
            return _reply(413, "File would exceed quota")
        token = self._key()
        upload = {
            **form,
            "url": f"https://uploads.zotero.example/{token}",
            "contentType": "multipart/form-data; boundary=x",
            "prefix": "--x\r\nContent-Type: application/pdf\r\n\r\n",
            "suffix": "\r\n--x--",
            "uploadKey": f"upload-{token}",
        }
        self.uploads[token] = upload
        return _reply(
            200,
            {
                name: upload[name]
                for name in ("url", "contentType", "prefix", "suffix", "uploadKey")
            },
        )

    def _write(self) -> int:
        self.version += 1
        return self.version


def _reply(
    status: int, body: object = b"", headers: dict | None = None
) -> zotero.Response:
    if not isinstance(body, bytes):
        body = (body if isinstance(body, str) else json.dumps(body)).encode()
    return zotero.Response(status, headers or {}, body)


def _page(objects: list[dict], query: dict) -> zotero.Response:
    start, limit = int(query.get("start", 0)), int(query.get("limit", 25))
    return _reply(
        200, objects[start : start + limit], {"Total-Results": str(len(objects))}
    )
