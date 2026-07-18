from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PageLink:
    text: str
    url: str


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def extract_competition_links(base_url: str, html: str) -> list[PageLink]:
    soup = BeautifulSoup(html, "html.parser")

    base_parsed = urlparse(base_url)
    competition_path = base_parsed.path.rstrip("/") + "/"

    links: list[PageLink] = []
    seen_urls: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()

        if not href:
            continue

        absolute_url = urljoin(base_url, href)
        parsed_url = urlparse(absolute_url)

        if parsed_url.netloc != base_parsed.netloc:
            continue

        if not parsed_url.path.startswith(competition_path):
            continue

        clean_url = parsed_url._replace(fragment="").geturl()

        if clean_url in seen_urls:
            continue

        seen_urls.add(clean_url)

        links.append(
            PageLink(
                text=normalize_text(tag.get_text(" ", strip=True)),
                url=clean_url,
            )
        )

    return links