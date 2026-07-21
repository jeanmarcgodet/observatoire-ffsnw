from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


CATEGORY_MAP = {
    "-8": "U8",
    "- 8": "U8",
    "8": "U8",
    "-10": "U10",
    "-12": "U12",
    "-14": "U14",
    "-17": "U17",
    "-18": "U18",
    "-21": "U21",
    "Ope": "Open",
    "OPEN": "Open",
    "open": "Open",
}


def clean(value: str) -> str:
    return " ".join(
        value.replace("\xa0", " ").split()
    )


def extract_iwwf_id(href: str) -> str | None:
    values = parse_qs(
        urlparse(href).query
    ).get("skier")

    if not values:
        return None

    return values[0].strip() or None


def normalize_category(value: str) -> tuple[str, str]:
    parts = clean(value).rsplit(" ", 1)

    if len(parts) != 2:
        raise RuntimeError(
            f"Catégorie non reconnue : {value!r}"
        )

    raw_category, sex = parts
    sex = sex.upper()

    if sex not in {"M", "F"}:
        raise RuntimeError(
            f"Sexe non reconnu : {value!r}"
        )

    category = CATEGORY_MAP.get(
        raw_category,
        raw_category,
    )

    return category, sex


def discipline_from_title(title: str) -> str:
    lowered = title.lower()

    for discipline in (
        "slalom",
        "tricks",
        "jump",
        "overall",
    ):
        if discipline in lowered:
            return discipline

    raise RuntimeError(
        f"Discipline non reconnue : {title}"
    )


def filename_prefix(
    category: str,
    sex: str,
) -> str:
    age_prefixes = {
        "U8": "8",
        "U10": "10",
        "U12": "12",
        "U14": "14",
        "U17": "17",
        "U18": "18",
        "U21": "21",
        "35+": "35",
        "45+": "45",
        "55+": "55",
        "65+": "65",
        "70+": "70",
        "75+": "75",
        "80+": "80",
    }

    if category == "Open":
        return (
            "men"
            if sex == "M"
            else "women"
        )

    prefix = age_prefixes.get(category)

    if prefix is None:
        raise RuntimeError(
            f"Catégorie non gérée : {category}"
        )

    return f"{prefix}_{sex.lower()}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("competition_code")
    args = parser.parse_args()

    code = args.competition_code.strip().upper()

    folder = (
        Path("data/raw/iwwf")
        / code
    )

    source = folder / f"{code}.html"

    if not source.is_file():
        source = folder / "index.html"

    if not source.is_file():
        raise FileNotFoundError(
            f"Page consolidée absente : {source}"
        )

    soup = BeautifulSoup(
        source.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
        "html.parser",
    )

    competition_title = (
        clean(
            soup.find("h1").get_text(
                " ",
                strip=True,
            )
        )
        if soup.find("h1")
        else code
    )

    generated = {}
    participants = {}
    source_rows = 0

    for heading in soup.find_all("h3"):
        title = clean(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        if "results" not in title.lower():
            continue

        try:
            discipline = discipline_from_title(
                title
            )
        except RuntimeError:
            continue

        table = heading.find_next("table")

        if table is None:
            continue

        rows = table.find_all("tr")

        header_row = None
        headers = None

        for row in rows:
            cells = row.find_all(
                ["th", "td"],
                recursive=False,
            )

            candidate_headers = [
                clean(
                    cell.get_text(
                        " ",
                        strip=True,
                    )
                )
                for cell in cells
            ]

            normalized = [
                value.lower()
                for value in candidate_headers
            ]

            if (
                "name" in normalized
                and any(
                    value in {
                        "categ.",
                        "categ",
                        "category",
                    }
                    for value in normalized
                )
            ):
                header_row = row
                headers = candidate_headers
                break

        if header_row is None or headers is None:
            continue

        normalized_headers = [
            value.lower()
            for value in headers
        ]

        name_index = normalized_headers.index(
            "name"
        )

        category_index = next(
            index
            for index, value
            in enumerate(normalized_headers)
            if value in {
                "categ.",
                "categ",
                "category",
            }
        )

        header_position = rows.index(header_row)

        groups = defaultdict(list)

        for row in rows[header_position + 1:]:
            cells = row.find_all(
                ["th", "td"],
                recursive=False,
            )

            if len(cells) <= max(
                name_index,
                category_index,
            ):
                continue

            name_cell = cells[name_index]
            link = name_cell.find(
                "a",
                href=True,
            )

            if link is None:
                continue

            iwwf_id = extract_iwwf_id(
                link.get("href", "")
            )

            if iwwf_id is None:
                continue

            name = clean(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            category_raw = clean(
                cells[category_index]
                .get_text(
                    " ",
                    strip=True,
                )
            )

            category, sex = normalize_category(
                category_raw
            )

            prefix = filename_prefix(
                category,
                sex,
            )

            filename = (
                f"{prefix}_{discipline}"
                "_results.html"
            )

            groups[filename].append(
                str(row)
            )

            participants[
                (
                    iwwf_id,
                    category,
                    sex,
                )
            ] = name

            source_rows += 1

        for filename, grouped_rows in groups.items():
            if filename in generated:
                raise RuntimeError(
                    "Classement présent dans plusieurs "
                    f"tableaux : {filename}"
                )

            generated[filename] = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(competition_title)} — {html.escape(title)}</title>
</head>
<body>
<h1>{html.escape(competition_title)}</h1>
<h3>{html.escape(title)}</h3>
<table>
{str(header_row)}
{chr(10).join(grouped_rows)}
</table>
</body>
</html>
"""

    if not generated:
        raise RuntimeError(
            "Aucun fichier de résultats généré."
        )

    for filename, content in generated.items():
        match = re.match(
            r"^(\d+)_[fm]_(slalom|tricks|jump|overall)"
            r"_results\.html$",
            filename,
        )

        if match is not None:
            category, discipline = match.groups()
            generic_file = (
                folder
                / f"{category}_{discipline}_results.html"
            )

            if generic_file.is_file():
                continue

        (folder / filename).write_text(
            content,
            encoding="utf-8",
        )

    participant_rows = []

    for (
        iwwf_id,
        category,
        sex,
    ), name in sorted(
        participants.items(),
        key=lambda item: (
            item[1],
            item[0][1],
            item[0][2],
        ),
    ):
        category_label = {
            "U8": "-8",
            "U10": "-10",
            "U12": "-12",
            "U14": "-14",
            "U17": "-17",
            "U18": "-18",
            "U21": "-21",
        }.get(
            category,
            category,
        )

        participant_rows.append(
            "<tr>"
            f'<td><a href="?skier={html.escape(iwwf_id)}">'
            f"{html.escape(name)}</a></td>"
            f"<td>{html.escape(category_label)} {sex}</td>"
            "</tr>"
        )

    participant_file = (
        folder / "all_skiers_list.html"
    )

    participant_file.write_text(
        f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(competition_title)} — Skiers</title>
</head>
<body>
<h1>{html.escape(competition_title)}</h1>
<table>
<tr><th>Name</th><th>Categ.</th></tr>
{chr(10).join(participant_rows)}
</table>
</body>
</html>
""",
        encoding="utf-8",
    )

    print("Compétition          :", code)
    print("Participants uniques :", len(participants))
    print("Fichiers générés     :", len(generated))
    print("Lignes sources       :", source_rows)


if __name__ == "__main__":
    main()
