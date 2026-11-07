"""web/public + page heads: crawler files, icons and social tags point at files that exist and agree on the domain."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

WEB = Path(__file__).resolve().parents[1] / "web"
PUBLIC = WEB / "public"
SITE = "https://twinbuild.click/"


def test_robots_allows_viewer_blocks_api_and_names_sitemap() -> None:
    robots = (PUBLIC / "robots.txt").read_text()
    assert "Allow: /\n" in robots
    assert "Disallow: /api/" in robots and "Disallow: /capture.html" in robots
    assert f"Sitemap: {SITE}sitemap.xml" in robots


def test_sitemap_lists_the_canonical_page() -> None:
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(PUBLIC / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
    assert locs == [SITE]


def test_manifest_icons_exist_with_declared_sizes() -> None:
    manifest = json.loads((PUBLIC / "site.webmanifest").read_text())
    for icon in manifest["icons"]:
        path = PUBLIC / icon["src"].lstrip("/")
        assert path.exists(), icon["src"]
        if icon["type"] == "image/png":
            w, h = icon["sizes"].split("x")
            assert Image.open(path).size == (int(w), int(h))


def test_index_head_references_existing_files_and_one_domain() -> None:
    html = (WEB / "index.html").read_text()
    for ref in re.findall(r'(?:href|content)="(/[^"/][^"]*)"', html):
        assert (PUBLIC / ref.lstrip("/")).exists(), ref
    for url in re.findall(r'"(https://[^"]+)"', html):
        assert url.startswith(SITE), url
    assert '<link rel="canonical" href="https://twinbuild.click/" />' in html
    assert Image.open(PUBLIC / "og-image.jpg").size == (1200, 630)


def test_snapshot_page_is_not_indexed() -> None:
    assert '<meta name="robots" content="noindex, nofollow" />' in (WEB / "capture.html").read_text()
