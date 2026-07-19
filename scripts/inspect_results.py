import sys
from pathlib import Path

from bs4 import BeautifulSoup


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage : python scripts/inspect_results.py "
            "<nom_du_fichier_html>"
        )
        raise SystemExit(1)

    filename = sys.argv[1]
    html_file = Path("data/raw/iwwf/26FRA021") / filename

    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    results_table = tables[3]

    print(f"Fichier : {filename}\n")

    for index, row in enumerate(
        results_table.find_all("tr")[:15],
        start=1,
    ):
        cells = row.find_all(["th", "td"], recursive=False)

        values = [
            cell.get_text(" ", strip=True)
            for cell in cells
        ]

        links = [
            {
                "texte": link.get_text(" ", strip=True),
                "href": link.get("href"),
            }
            for link in row.find_all("a", href=True)
        ]

        print("=" * 80)
        print(f"LIGNE {index}")
        print("Nombre de cellules :", len(cells))
        print("Valeurs :", values)
        print("Liens   :", links)

        if not values or len(values) < 6:
            print("HTML BRUT :")
            print(row.prettify())

        print()


if __name__ == "__main__":
    main()