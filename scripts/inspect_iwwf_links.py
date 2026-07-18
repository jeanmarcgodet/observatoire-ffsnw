from pathlib import Path

from bs4 import BeautifulSoup


HTML_FILE = Path("data/raw/iwwf/26FRA021.html")


if __name__ == "__main__":
    html = HTML_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )

    soup = BeautifulSoup(html, "html.parser")

    links = soup.find_all("a", href=True)

    print(f"{len(links)} balise(s) <a href> détectée(s)\n")

    for index, tag in enumerate(links, start=1):
        text = " ".join(tag.get_text(" ", strip=True).split())
        href = tag.get("href", "").strip()

        print(f"{index:03d}. {text or '[sans texte]'}")
        print(f"     {href}")