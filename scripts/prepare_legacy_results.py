from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup


HEADING_PATTERN = re.compile(
    r"^Under\s+(\d+)\s+"
    r"(Girls|Boys|Women|Men)\s+"
    r"(Slalom|Tricks|Jump|Overall)\s+"
    r"Results$",
    flags=re.IGNORECASE,
)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value.upper(),
    )

    return " ".join(value.split())


def load_identity_map(
    identity_file: Path,
) -> dict[str, str]:
    data = json.loads(
        identity_file.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Format JSON invalide : {identity_file}"
        )

    identities: dict[str, str] = {}

    for raw_name, identity in data.items():
        if not isinstance(identity, dict):
            continue

        ranking_id = str(
            identity.get("ranking_id")
            or ""
        ).strip().upper()

        if not ranking_id:
            raise RuntimeError(
                "Identifiant IWWF manquant pour "
                f"{raw_name}"
            )

        names = {
            str(raw_name),
            str(
                identity.get("source_name")
                or ""
            ),
        }

        candidates = identity.get("candidates")

        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue

                candidate_id = str(
                    candidate.get("ranking_id")
                    or ""
                ).strip().upper()

                candidate_name = str(
                    candidate.get("candidate_name")
                    or ""
                ).strip()

                if (
                    candidate_id == ranking_id
                    and candidate_name
                ):
                    names.add(candidate_name)

        for name in names:
            key = normalize_name(name)

            if not key:
                continue

            existing = identities.get(key)

            if (
                existing is not None
                and existing != ranking_id
            ):
                raise RuntimeError(
                    "Conflit d'identité pour "
                    f"{name} : {existing} / {ranking_id}"
                )

            identities[key] = ranking_id

    return identities


def get_direct_cells(row):
    return row.find_all(
        ["th", "td"],
        recursive=False,
    )


def find_name_index(table) -> int:
    for row in table.find_all("tr"):
        cells = get_direct_cells(row)

        headers = [
            " ".join(
                cell.get_text(
                    " ",
                    strip=True,
                ).split()
            ).lower()
            for cell in cells
        ]

        if "name" in headers:
            return headers.index("name")

    raise RuntimeError(
        "Colonne Name introuvable."
    )


def get_output_filename(
    title: str,
) -> str:
    match = HEADING_PATTERN.match(title)

    if match is None:
        raise RuntimeError(
            f"Titre non reconnu : {title}"
        )

    age, sex_label, discipline = match.groups()

    sex = (
        "f"
        if sex_label.lower()
        in {"girls", "women"}
        else "m"
    )

    return (
        f"{age}_{sex}_"
        f"{discipline.lower()}_results.html"
    )


def prepare_legacy_results(
    competition_code: str,
    raw_root: Path,
) -> tuple[int, int]:
    directory = raw_root / competition_code

    source_file = (
        directory
        / f"{competition_code}.html"
    )

    if not source_file.is_file():
        source_file = directory / "index.html"

    if not source_file.is_file():
        raise FileNotFoundError(
            "Page consolidée introuvable : "
            f"{source_file}"
        )

    identity_files = sorted(
        directory.glob(
            "identity_candidates*.json"
        )
    )

    if not identity_files:
        raise FileNotFoundError(
            "Fichier d'identités introuvable dans "
            f"{directory}"
        )

    identity_file = identity_files[0]
    identity_map = load_identity_map(
        identity_file
    )

    soup = BeautifulSoup(
        source_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ),
        "html.parser",
    )

    competition_title = (
        soup.find("h1").get_text(
            " ",
            strip=True,
        )
        if soup.find("h1")
        else competition_code
    )

    generated: dict[str, str] = {}
    result_rows = 0
    missing_names: set[str] = set()

    for heading in soup.find_all("h3"):
        title = " ".join(
            heading.get_text(
                " ",
                strip=True,
            ).split()
        )

        if HEADING_PATTERN.match(title) is None:
            continue

        table = heading.find_next("table")

        if table is None:
            raise RuntimeError(
                f"Tableau absent après : {title}"
            )

        filename = get_output_filename(title)

        if filename in generated:
            raise RuntimeError(
                f"Fichier généré en double : {filename}"
            )

        name_index = find_name_index(table)
        rows = table.find_all("tr")

        table_rows = 0

        for row in rows[1:]:
            cells = get_direct_cells(row)

            if len(cells) <= name_index:
                continue

            name_cell = cells[name_index]

            name = " ".join(
                name_cell.get_text(
                    " ",
                    strip=True,
                ).split()
            )

            if not name:
                continue

            iwwf_id = identity_map.get(
                normalize_name(name)
            )

            if iwwf_id is None:
                missing_names.add(name)
                continue

            name_cell.clear()

            link = soup.new_tag(
                "a",
                href=f"?skier={iwwf_id}",
            )
            link.string = name
            name_cell.append(link)

            table_rows += 1

        result_rows += table_rows

        generated[filename] = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(competition_title)} — {html.escape(title)}</title>
</head>
<body>
<h1>{html.escape(competition_title)}</h1>
<h3>{html.escape(title)}</h3>
{str(table)}
</body>
</html>
"""

    if missing_names:
        raise RuntimeError(
            "Identités introuvables : "
            + ", ".join(
                sorted(missing_names)
            )
        )

    if not generated:
        raise RuntimeError(
            "Aucun tableau de résultats reconnu."
        )

    for filename, content in generated.items():
        output_file = directory / filename

        output_file.write_text(
            content,
            encoding="utf-8",
        )

    return len(generated), result_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transforme une ancienne page IWWF consolidée "
            "en fichiers *_results.html standards."
        )
    )

    parser.add_argument(
        "competition_code",
    )

    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/raw/iwwf"),
    )

    args = parser.parse_args()

    files_count, rows_count = (
        prepare_legacy_results(
            competition_code=(
                args.competition_code.strip()
            ),
            raw_root=args.raw_root,
        )
    )

    print()
    print(
        "Compétition       :",
        args.competition_code,
    )
    print(
        "Fichiers générés  :",
        files_count,
    )
    print(
        "Lignes compétiteur:",
        rows_count,
    )


if __name__ == "__main__":
    main()
