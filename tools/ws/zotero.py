"""A Zotero library, by its Web API: the source of every repository's bibliography.

`ws` only ever adds to the library (items, collection memberships, a citekey where
there was none, PDF attachments); it never changes or deletes a value already set.
"""

import hashlib
import json
import re
import string
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from ws import retrieve

API = "https://api.zotero.org"
# Objects per page; the most the Web API returns at once.
_PAGE = 100
# Title words a citekey skips, as Better BibTeX does.
_SKIPPED = {
    "a", "an", "the", "and", "or", "but", "nor", "of", "on", "in", "at", "to", "for",
    "from", "by", "with", "as", "about", "into", "over", "is", "are", "de", "la", "le",
    "les", "des", "du", "der", "die", "das", "und", "von",
}


@dataclass(frozen=True)
class Response:
    """What a server answered: its status, headers and body."""

    status: int
    headers: dict[str, str]
    body: bytes


# Sends a request (method, URL, headers, body); returns the answer, whatever its
# status, or raises `OSError` if no server answered.
Send = Callable[[str, str, dict[str, str], bytes | None], Response]


def send(
    method: str, url: str, headers: dict[str, str], body: bytes | None = None
) -> Response:
    """Send a request to the web."""
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"User-Agent": "research-ws", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return Response(response.status, dict(response.headers), response.read())
    except urllib.error.HTTPError as error:
        return Response(error.code, dict(error.headers), error.read())


def _header(response: Response, name: str) -> str:
    """A header of the response, whatever its case."""
    for key, value in response.headers.items():
        if key.lower() == name.lower():
            return value
    raise ZoteroError(f"Zotero answered with no {name} header")


class ZoteroError(Exception):
    """Zotero refused or failed a request."""


class Unreachable(ZoteroError):
    """No answer from Zotero: the network is down, or the server is."""


class QuotaFull(ZoteroError):
    """The library's file storage has no room for a file."""


class ReadOnly(ZoteroError):
    """The key may read the library but not write to it."""

    def __init__(self) -> None:
        super().__init__(
            "the Zotero key is read-only: give it write access to the library"
        )


def citekey(data: dict) -> str | None:
    """The citekey Zotero holds for an item: Zotero 7's field, or Better BibTeX's line in Extra."""
    if data.get("citationKey"):
        return data["citationKey"]
    for line in data.get("extra", "").splitlines():
        name, _, value = line.partition(":")
        if name.strip().lower() == "citation key" and value.strip():
            return value.strip()
    return None


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def made_citekey(data: dict) -> str:
    """A citekey for an item without one: the first author's last name, the year and the
    title's first significant word, lowercased (`raissi2019physics`).
    """
    creators = data.get("creators", [])
    authors = [
        creator for creator in creators if creator.get("creatorType") == "author"
    ]
    first = (authors or creators or [{}])[0]
    name = re.sub(
        r"[^a-z0-9-]",
        "",
        _ascii(first.get("lastName") or first.get("name", "")).lower(),
    )
    year = re.search(r"\b(\d{4})\b", data.get("date", ""))
    words = re.findall(r"[a-z0-9]+", _ascii(data.get("title", "")).lower())
    word = next((word for word in words if word not in _SKIPPED), "")
    return f"{name or 'anon'}{year.group(1) if year else ''}{word}"


@dataclass
class Library:
    """A Zotero library (`users/<id>` or `groups/<id>`) and the key that opens it."""

    library: str
    api_key: str
    send: Send = send
    upload_pdfs: bool = False

    def _request(
        self,
        method: str,
        path: str,
        body: object = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = f"{API}/{self.library}/{path}"
        # A form is sent as it is; anything else, as JSON.
        json_body = body is not None and not isinstance(body, bytes)
        data = json.dumps(body).encode() if json_body else body
        try:
            response = self.send(
                method,
                url,
                {
                    "Zotero-API-Key": self.api_key,
                    "Zotero-API-Version": "3",
                    **({"Content-Type": "application/json"} if json_body else {}),
                    **(headers or {}),
                },
                data,
            )
        except OSError as error:
            raise Unreachable(f"Zotero is unreachable: {error}") from error
        if response.status == 403 and method != "GET":
            raise ReadOnly()
        if response.status == 413:
            raise QuotaFull("Zotero's file storage is full")
        if response.status >= 400:
            message = response.body.decode(errors="replace").strip()
            raise ZoteroError(
                f"Zotero answered {method} {path} with {response.status}: {message}"
            )
        return response

    def _json(
        self, method: str, path: str, body: object = None, **headers: str
    ) -> object:
        response = self._request(method, path, body, headers)
        try:
            return json.loads(response.body) if response.body else None
        except ValueError as error:
            raise ZoteroError(f"Zotero answered {path} with no JSON") from error

    def _all(self, path: str) -> list[dict]:
        """Every object at `path`, page by page."""
        found: list[dict] = []
        separator = "&" if "?" in path else "?"
        while True:
            page = self._json(
                "GET", f"{path}{separator}format=json&limit={_PAGE}&start={len(found)}"
            )
            if not isinstance(page, list):
                raise ZoteroError(f"Zotero answered {path} with no list")
            found += page
            if len(page) < _PAGE:
                return found

    def collection(self, names: list[str]) -> str | None:
        """The key of the collection at the path `names` from the library's top, or None."""
        collections = self._all("collections")
        parent: str | bool = False
        for name in names:
            matches = [
                collection["key"]
                for collection in collections
                if collection["data"]["name"] == name
                and collection["data"].get("parentCollection", False) == parent
            ]
            if not matches:
                return None
            parent = matches[0]
        return parent or None

    def create_collection(self, name: str, parent: str | None = None) -> str:
        """Create a collection, under `parent` if given; returns its key.

        Raises `ReadOnly` if the key cannot write.
        """
        answer = self._json(
            "POST", "collections", [{"name": name, "parentCollection": parent or False}]
        )
        if not isinstance(answer, dict) or "0" not in answer.get("successful", {}):
            raise ZoteroError(f"Zotero did not create the collection {name}: {answer}")
        return answer["successful"]["0"]["key"]

    def items(self, collection: str) -> list[dict]:
        """The data of the top-level items of a collection: no attachments or notes."""
        return [
            item["data"] for item in self._all(f"collections/{collection}/items/top")
        ]

    def search(self, text: str) -> list[dict]:
        """The data of every top-level item holding `text` in any of its fields."""
        query = urllib.parse.quote(text)
        return [
            item["data"] for item in self._all(f"items/top?q={query}&qmode=everything")
        ]

    def unique_citekey(self, data: dict, taken: set[str]) -> str:
        """A citekey for `data`, held by no item of the library and not in `taken`."""
        base = made_citekey(data)
        for suffix in ["", *string.ascii_lowercase]:
            key = base + suffix
            if key not in taken and not any(
                citekey(other) == key for other in self.search(key)
            ):
                return key
        raise ZoteroError(f"no free citekey from {base}: give the item one in Zotero")

    def add(self, data: dict, **fields: object) -> None:
        """Write fields of an item: ones it had no value in, or a list it grows.

        Raises `ReadOnly` if the key cannot write.
        """
        response = self._request(
            "PATCH",
            f"items/{data['key']}",
            fields,
            {"If-Unmodified-Since-Version": str(data["version"])},
        )
        data.update(fields)
        data["version"] = int(_header(response, "Last-Modified-Version"))

    def create(self, data: dict) -> dict:
        """Create an item; returns its data. Raises `ReadOnly` if the key cannot write."""
        answer = self._json("POST", "items", [data])
        if not isinstance(answer, dict) or "0" not in answer.get("successful", {}):
            failed = (
                (answer or {}).get("failed", {}).get("0", {})
                if isinstance(answer, dict)
                else {}
            )
            raise ZoteroError(
                f"Zotero did not create the item: {failed.get('message', answer)}"
            )
        created = answer["successful"]["0"]
        return {
            **created.get("data", {}),
            "key": created["key"],
            "version": created["version"],
        }

    def attach_pdf(self, key: str, pdf: bytes) -> None:
        """Attach `pdf` to the item with the citekey `key`, as the file `<key>.pdf`.

        Raises `QuotaFull`, leaving no attachment behind, if the library's file storage
        has no room for it.
        """
        items = [data for data in self.search(key) if citekey(data) == key]
        if not items:
            raise ZoteroError(f"no item with the citekey {key}")
        filename = f"{key}.pdf"
        attachment = self.create(
            {
                "itemType": "attachment",
                "parentItem": items[0]["key"],
                "linkMode": "imported_file",
                "title": "Full Text PDF",
                "contentType": "application/pdf",
                "filename": filename,
                "tags": [],
                "relations": {},
            }
        )
        path = f"items/{attachment['key']}/file"
        form = {
            "Content-Type": "application/x-www-form-urlencoded",
            "If-None-Match": "*",
        }
        try:
            answer = self._json(
                "POST",
                path,
                urllib.parse.urlencode(
                    {
                        "md5": hashlib.md5(pdf).hexdigest(),
                        "filename": filename,
                        "filesize": len(pdf),
                        "mtime": int(time.time() * 1000),
                    }
                ).encode(),
                **form,
            )
        except QuotaFull:
            # The attachment made for it would stay empty: it goes, as it came, with `ws`.
            self._request(
                "DELETE",
                f"items/{attachment['key']}",
                headers={"If-Unmodified-Since-Version": str(attachment["version"])},
            )
            raise
        if not isinstance(answer, dict):
            raise ZoteroError(f"Zotero answered {path} with no upload")
        if answer.get("exists"):
            return
        try:
            uploaded = self.send(
                "POST",
                answer["url"],
                {"Content-Type": answer["contentType"]},
                answer["prefix"].encode() + pdf + answer["suffix"].encode(),
            )
        except OSError as error:
            raise Unreachable(
                f"Zotero's file storage is unreachable: {error}"
            ) from error
        if uploaded.status != 201:
            raise ZoteroError(f"Zotero's file storage answered {uploaded.status}")
        self._request(
            "POST",
            path,
            urllib.parse.urlencode({"upload": answer["uploadKey"]}).encode(),
            form,
        )


def configured(
    send: Send = send, workspace: str | None = None
) -> tuple[Library | None, str]:
    """The library of the user's configuration for `workspace`; or None, and why there
    is none.
    """
    config, problems, path = retrieve.settings(workspace)
    if problems:
        return None, "; ".join(problems)
    settings = config.get("zotero")
    if settings is None:
        return None, f"no Zotero configuration in {path}"
    if not (
        isinstance(settings, dict)
        and isinstance(settings.get("library"), str)
        and isinstance(settings.get("api_key"), str)
    ):
        return None, f"{path}: zotero needs a library and an api_key"
    return (
        Library(
            settings["library"].strip("/"),
            settings["api_key"],
            send,
            config.get("upload_pdfs") is True,
        ),
        "",
    )
