"""Check internal links in the built MkDocs site.

Standard library only. Parses every HTML file under ``site/`` and verifies that
each internal link resolves: relative links point to an existing file,
directory links resolve to ``index.html``, fragment anchors (``#section``) exist
in the target page, and local image/script/style references exist.

External links (http/https, mailto, tel, javascript, data) and empty anchors are
ignored. Exits non-zero and prints each broken link if any are found.

Usage:
    python scripts/check_docs_links.py [site_dir]
"""

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

_EXTERNAL_SCHEMES = frozenset({"http", "https", "mailto", "tel", "javascript", "data", "ftp"})


class _LinkExtractor(HTMLParser):
    """Collect element ids and internal link/reference targets from one page."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []

    def _consume(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v for k, v in attrs if v is not None}
        if attr.get("id"):
            self.ids.add(attr["id"])
        if tag == "a" and attr.get("name"):
            self.ids.add(attr["name"])
        if tag in ("a", "link") and attr.get("href"):
            self.links.append(attr["href"])
        if tag in ("img", "script", "source") and attr.get("src"):
            self.links.append(attr["src"])

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._consume(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._consume(tag, attrs)


def _is_external(link: str) -> bool:
    return link.startswith("//") or urlsplit(link).scheme in _EXTERNAL_SCHEMES


def _resolve(site: Path, page: Path, path_part: str) -> Path:
    """Resolve a link's path (relative to ``page``, or absolute to ``site``)."""
    if path_part.startswith("/"):
        candidate = site / path_part.lstrip("/")
    else:
        candidate = page.parent / path_part
    if path_part.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate.resolve()


def check_site(site: Path) -> list[str]:
    """Return a list of human-readable errors for broken internal links."""
    html_files = sorted(site.rglob("*.html"))
    ids_by_file: dict[Path, set[str]] = {}
    links_by_file: dict[Path, list[str]] = {}
    for path in html_files:
        parser = _LinkExtractor()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        ids_by_file[path.resolve()] = parser.ids
        links_by_file[path] = parser.links

    # 404.html is generated with absolute base-path links (valid only on the
    # deployed site, not in the local tree), so it is not checked here.
    pages = [p for p in html_files if p.name != "404.html"]

    errors: list[str] = []
    for page in pages:
        for raw in links_by_file[page]:
            link = raw.strip()
            if not link or _is_external(link):
                continue
            parts = urlsplit(link)
            path_part = unquote(parts.path)
            fragment = parts.fragment

            target = page.resolve() if path_part == "" else _resolve(site, page, path_part)

            if not target.exists():
                errors.append(f"{page}: {link} -> missing target {target}")
                continue
            if fragment and target.suffix == ".html":
                anchors = ids_by_file.get(target)
                if anchors is not None and fragment not in anchors:
                    errors.append(f"{page}: {link} -> missing anchor #{fragment}")
    return errors


def main(argv: list[str]) -> int:
    site = Path(argv[1]) if len(argv) > 1 else Path("site")
    if not site.is_dir():
        print(f"{site}/ not found — run `make docs` first", file=sys.stderr)
        return 2

    errors = check_site(site)
    if errors:
        print(f"Found {len(errors)} broken internal link(s):", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    checked = len(list(site.rglob("*.html")))
    print(f"OK: internal links valid across {checked} HTML file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
