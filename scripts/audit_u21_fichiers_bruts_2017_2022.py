"""Audite les catégories U21 dans les fichiers historiques bruts IWWF.

But
---
Vérifier si les catégories U21 2017-2022, absentes de la base SQLite actuelle,
sont encore présentes dans les fichiers historiques sous :
    data/raw/iwwf/<CODE>/

Le script recherche notamment :
- all_skiers_list.html ;
- <CODE>.html ;
- index.html ;
- les fichiers *_results.html.

Il ne modifie aucune donnée existante.

Sorties
-------
data/processed/audit_u21_fichiers_bruts_2017_2022.csv
data/processed/audit_u21_individus_fichiers_bruts_2017_2022.csv
data/exports/audit_u21_fichiers_bruts_2017_2022.txt
"""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


START_YEAR = 2017
END_YEAR = 2022


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def is_u21_label(value: str | None) -> bool:
    category = normalize(value)
    return bool(
        re.search(r"(^|[^0-9])U[\s_-]?21([^0-9]|$)", category)
        or re.search(r"(^|[^0-9])-21([^0-9]|$)", category)
        or re.search(r"(^|[^0-9])21\s*[MF]?([^0-9]|$)", category)
        or "UNDER 21" in category
    )


def extract_skier_id(href: str | None) -> str:
    if not href:
        return ""
    values = parse_qs(urlparse(href).query).get("skier")
    return values[0].strip() if values else ""


def read_old_counts(path: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    if not path.exists():
        return counts

    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            if normalize(row.get("categorie")) != "U21":
                continue
            try:
                year = int((row.get("annee") or "").strip())
                participants = int((row.get("participants") or "0").strip())
            except ValueError:
                continue
            counts[year] = participants
    return counts


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def candidate_files(folder: Path, code: str) -> list[Path]:
    candidates: list[Path] = []

    preferred = (
        folder / "all_skiers_list.html",
        folder / f"{code}.html",
        folder / "index.html",
    )
    for path in preferred:
        if path.is_file():
            candidates.append(path)

    for path in sorted(folder.glob("*_results.html")):
        if path not in candidates:
            candidates.append(path)

    return candidates


def parse_html(path: Path) -> list[dict[str, str]]:
    soup = BeautifulSoup(
        path.read_text(encoding="utf-8", errors="ignore"),
        "html.parser",
    )
    found: list[dict[str, str]] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        header_index = None
        name_index = None
        category_index = None

        for index, row in enumerate(rows):
            cells = row.find_all(["th", "td"], recursive=False)
            headers = [
                normalize(cell.get_text(" ", strip=True))
                for cell in cells
            ]

            if not headers:
                continue

            for position, header in enumerate(headers):
                if header in {"NAME", "SKIER", "ATHLETE"}:
                    name_index = position
                if header in {"CATEG.", "CATEG", "CATEGORY", "CATÉGORIE", "CATEGORIE"}:
                    category_index = position

            if name_index is not None and category_index is not None:
                header_index = index
                break

        if header_index is None or name_index is None or category_index is None:
            continue

        for row in rows[header_index + 1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) <= max(name_index, category_index):
                continue

            name_cell = cells[name_index]
            category_raw = cells[category_index].get_text(" ", strip=True)

            if not is_u21_label(category_raw):
                continue

            link = name_cell.find("a", href=True)
            name = name_cell.get_text(" ", strip=True)
            skier_id = extract_skier_id(link.get("href")) if link else ""

            found.append(
                {
                    "SourceFile": str(path),
                    "SkierId": skier_id,
                    "Name": name,
                    "CategoryRaw": category_raw,
                }
            )

    # Les fichiers nommés 21_f_* ou 21_m_* portent déjà la catégorie.
    filename_match = re.match(
        r"^21_([fm])_(slalom|tricks|jump|overall)_results\.html$",
        path.name.lower(),
    )
    if filename_match and not found:
        soup = BeautifulSoup(
            path.read_text(encoding="utf-8", errors="ignore"),
            "html.parser",
        )
        for link in soup.find_all("a", href=True):
            skier_id = extract_skier_id(link.get("href"))
            if not skier_id:
                continue
            found.append(
                {
                    "SourceFile": str(path),
                    "SkierId": skier_id,
                    "Name": link.get_text(" ", strip=True),
                    "CategoryRaw": f"-21 {filename_match.group(1).upper()}",
                }
            )

    return found


def main() -> None:
    root = repo_root()
    raw_root = root / "data/raw/iwwf"
    db_path = root / "data/observatoire.db"
    old_counts = read_old_counts(
        root / "data/exports/participation_categories_2017_2026.csv"
    )

    if not db_path.exists():
        raise FileNotFoundError(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    competitions = conn.execute(
        """
        SELECT annee, iwwf_id, nom
        FROM competitions
        WHERE annee BETWEEN ? AND ?
          AND niveau = 'championnat_france'
        ORDER BY annee, iwwf_id
        """,
        (START_YEAR, END_YEAR),
    ).fetchall()
    conn.close()

    summary_rows: list[dict[str, object]] = []
    individual_rows: list[dict[str, object]] = []

    unique_by_year: dict[int, set[str]] = defaultdict(set)
    names_by_year: dict[int, set[str]] = defaultdict(set)

    for competition in competitions:
        year = int(competition["annee"])
        code = (competition["iwwf_id"] or "").strip()
        name = (competition["nom"] or "").strip()
        folder = raw_root / code

        files = candidate_files(folder, code) if folder.is_dir() else []
        competition_people: dict[str, dict[str, str]] = {}

        for source_file in files:
            for person in parse_html(source_file):
                identity = (
                    person["SkierId"]
                    or normalize(person["Name"])
                )
                if not identity:
                    continue
                competition_people.setdefault(identity, person)

        for identity, person in sorted(competition_people.items()):
            unique_by_year[year].add(identity)
            names_by_year[year].add(normalize(person["Name"]))
            individual_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "CompetitionName": name,
                    "IdentityKey": identity,
                    "SkierId": person["SkierId"],
                    "Name": person["Name"],
                    "CategoryRaw": person["CategoryRaw"],
                    "SourceFile": person["SourceFile"],
                }
            )

        summary_rows.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionName": name,
                "RawFolderExists": int(folder.is_dir()),
                "CandidateHtmlFiles": len(files),
                "U21DistinctInCompetition": len(competition_people),
                "FilesScanned": " | ".join(
                    str(path.relative_to(root)) for path in files
                ),
            }
        )

    lines: list[str] = []
    lines.append("AUDIT U21 DANS LES FICHIERS BRUTS IWWF — 2017-2022")
    lines.append("=" * 88)
    lines.append("")
    lines.append("1. EFFECTIFS DISTINCTS TROUVÉS")
    lines.append("-" * 88)
    lines.append("Année | U21 fichiers bruts | ancien export | concordance")

    for year in range(START_YEAR, END_YEAR + 1):
        raw_count = len(unique_by_year[year])
        old_count = old_counts.get(year)
        match = (
            "OUI"
            if old_count is not None and raw_count == old_count
            else "NON"
            if old_count is not None
            else "n.d."
        )
        lines.append(
            f"{year} | {raw_count} | "
            f"{old_count if old_count is not None else 'n.d.'} | {match}"
        )

    lines.append("")
    lines.append("2. COMPÉTITIONS ET FICHIERS DISPONIBLES")
    lines.append("-" * 88)
    for row in summary_rows:
        lines.append(
            f"{row['Year']} — {row['CompetitionCode']} — "
            f"{row['CompetitionName']} : dossier={row['RawFolderExists']} ; "
            f"fichiers={row['CandidateHtmlFiles']} ; "
            f"U21={row['U21DistinctInCompetition']}."
        )
        if row["FilesScanned"]:
            lines.append(f"    {row['FilesScanned']}")

    lines.append("")
    lines.append("3. INDIVIDUS U21 TROUVÉS")
    lines.append("-" * 88)
    if not individual_rows:
        lines.append("Aucun U21 trouvé dans les fichiers disponibles.")
    else:
        for row in individual_rows:
            lines.append(
                f"{row['Year']} — {row['CompetitionCode']} — "
                f"{row['Name']} — {row['CategoryRaw']} — "
                f"id={row['SkierId'] or 'sans identifiant'}."
            )

    lines.append("")
    lines.append("4. CONCLUSION AUTOMATIQUE")
    lines.append("-" * 88)

    matched_years = [
        year
        for year in range(START_YEAR, END_YEAR + 1)
        if year in old_counts
        and len(unique_by_year[year]) == old_counts[year]
    ]
    differing_years = [
        year
        for year in range(START_YEAR, END_YEAR + 1)
        if year in old_counts
        and len(unique_by_year[year]) != old_counts[year]
    ]

    if matched_years:
        lines.append(
            "Les fichiers bruts reproduisent l'ancien export pour : "
            + ", ".join(str(year) for year in matched_years)
            + "."
        )
    if differing_years:
        lines.append(
            "Des écarts persistent pour : "
            + ", ".join(str(year) for year in differing_years)
            + "."
        )

    if individual_rows:
        lines.append(
            "Les catégories U21 historiques sont encore récupérables dans "
            "les fichiers bruts ; la base SQLite actuelle est incomplète sur ce point."
        )
    else:
        lines.append(
            "Les fichiers bruts disponibles ne permettent pas encore de "
            "retrouver les U21 historiques."
        )

    lines.append("")
    lines.append("FIN DE L'AUDIT")

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "audit_u21_fichiers_bruts_2017_2022.csv",
        summary_rows,
        [
            "Year",
            "CompetitionCode",
            "CompetitionName",
            "RawFolderExists",
            "CandidateHtmlFiles",
            "U21DistinctInCompetition",
            "FilesScanned",
        ],
    )
    write_csv(
        processed / "audit_u21_individus_fichiers_bruts_2017_2022.csv",
        individual_rows,
        [
            "Year",
            "CompetitionCode",
            "CompetitionName",
            "IdentityKey",
            "SkierId",
            "Name",
            "CategoryRaw",
            "SourceFile",
        ],
    )

    output = exports / "audit_u21_fichiers_bruts_2017_2022.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("AUDIT DES FICHIERS BRUTS U21 TERMINE")
    print("=" * 88)
    print(f"Individus U21 trouvés : {len(individual_rows)} lignes compétition")
    print(f"Rapport : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
