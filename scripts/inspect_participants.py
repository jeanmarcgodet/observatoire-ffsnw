from pathlib import Path

from bs4 import BeautifulSoup


html_file = Path(
    "data/raw/iwwf/26FRA021/all_skiers_list.html"
)

html = html_file.read_text(
    encoding="utf-8",
    errors="ignore",
)

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table")

participants_table = tables[3]

for index, row in enumerate(
    participants_table.find_all("tr")[:10],
    start=1,
):
    cells = row.find_all(["th", "td"])

    values = [
        cell.get_text(" ", strip=True)
        for cell in cells
    ]

    links = [
        {
            "texte": link.get_text(" ", strip=True),
            "href": link.get("href"),
        }
        for link in row.find_all("a")
    ]

    print(f"LIGNE {index}")
    print("Valeurs :", values)
    print("Liens   :", links)
    print()