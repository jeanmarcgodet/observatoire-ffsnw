"""Audite les U21 sur les codes historiques explicitement utilisés par les anciens scripts.

Pourquoi ce script
-------------------
Les audits précédents filtraient `competitions.niveau = championnat_france`.
Or les anciens scripts de trajectoire ne s'appuyaient pas sur ce champ :
ils sélectionnaient explicitement plusieurs codes par année, notamment les
championnats U21 séparés. Ce script reproduit ce périmètre historique.

Aucune donnée existante n'est modifiée.

Sorties
-------
data/processed/audit_u21_codes_explicites_2017_2022.csv
data/processed/audit_u21_individus_codes_explicites_2017_2022.csv
data/exports/audit_u21_codes_explicites_2017_2022.txt
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


BASE_CODES = (
    "17FRA002", "17FRA005",
    "18FRA001", "18FRA010", "18FRA030",
    "19FRA001", "19FRA002", "19FRA03",
    "20FRA029", "20FRA030", "20FRA031",
    "21FRA044", "21FRA045", "21FRA046",
    "22FRA029", "22FRA030", "22FRA031",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def is_u21(value: str | None) -> bool:
    text = normalize(value)
    return bool(
        re.search(r"(^|[^0-9])U[\s_-]?21([^0-9]|$)", text)
        or re.search(r"(^|[^0-9])-21([^0-9]|$)", text)
        or "UNDER 21" in text
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
                counts[int(row["annee"])] = int(row["participants"])
            except (KeyError, TypeError, ValueError):
                continue
    return counts


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def resolve_codes(root: Path, db_codes: set[str]) -> list[str]:
    raw_root = root / "data/raw/iwwf"
    resolved: list[str] = []

    for code in BASE_CODES:
        if code != "19FRA03":
            resolved.append(code)
            continue

        matches = sorted(
            {
                candidate
                for candidate in db_codes
                if candidate.startswith("19FRA03")
            }
            | {
                folder.name
                for folder in raw_root.glob("19FRA03*")
                if folder.is_dir()
            }
        )

        if matches:
            resolved.extend(matches)
        else:
            resolved.append(code)

    return list(dict.fromkeys(resolved))


def parse_u21_from_html(path: Path) -> list[dict[str, str]]:
    soup = BeautifulSoup(
        path.read_text(encoding="utf-8", errors="ignore"),
        "html.parser",
    )
    found: dict[str, dict[str, str]] = {}

    # Cas des fichiers explicitement nommés 21_f_* ou 21_m_*.
    filename_match = re.match(
        r"^21_([fm])_(slalom|tricks|jump|overall)_results\.html$",
        path.name.lower(),
    )
    inferred_sex = filename_match.group(1).upper() if filename_match else ""

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        header_position = None
        name_index = None
        category_index = None

        for index, row in enumerate(rows):
            cells = row.find_all(["th", "td"], recursive=False)
            headers = [normalize(cell.get_text(" ", strip=True)) for cell in cells]

            local_name = next(
                (
                    pos for pos, header in enumerate(headers)
                    if header in {"NAME", "SKIER", "ATHLETE"}
                ),
                None,
            )
            local_category = next(
                (
                    pos for pos, header in enumerate(headers)
                    if header in {
                        "CATEG.", "CATEG", "CATEGORY",
                        "CATEGORIE", "CATÉGORIE",
                    }
                ),
                None,
            )

            if local_name is not None and (
                local_category is not None or filename_match is not None
            ):
                header_position = index
                name_index = local_name
                category_index = local_category
                break

        if header_position is None or name_index is None:
            continue

        for row in rows[header_position + 1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) <= name_index:
                continue

            category_raw = ""
            if category_index is not None and len(cells) > category_index:
                category_raw = cells[category_index].get_text(" ", strip=True)

            if not filename_match and not is_u21(category_raw):
                continue

            name_cell = cells[name_index]
            link = name_cell.find("a", href=True)
            name = name_cell.get_text(" ", strip=True)
            skier_id = extract_skier_id(link.get("href")) if link else ""

            identity = skier_id or normalize(name)
            if not identity:
                continue

            found.setdefault(
                identity,
                {
                    "SkierId": skier_id,
                    "Name": name,
                    "CategoryRaw": category_raw or f"-21 {inferred_sex}",
                    "SourceFile": str(path),
                },
            )

    return list(found.values())


def main() -> None:
    root = repo_root()
    db_path = root / "data/observatoire.db"
    raw_root = root / "data/raw/iwwf"
    old_counts = read_old_counts(
        root / "data/exports/participation_categories_2017_2026.csv"
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    db_competitions = conn.execute(
        """
        SELECT annee, iwwf_id, nom, niveau
        FROM competitions
        WHERE annee BETWEEN 2017 AND 2022
        ORDER BY annee, iwwf_id
        """
    ).fetchall()
    db_codes = {str(row["iwwf_id"]) for row in db_competitions}

    codes = resolve_codes(root, db_codes)
    placeholders = ",".join("?" for _ in codes)

    competition_rows = conn.execute(
        f"""
        SELECT annee, iwwf_id, nom, niveau
        FROM competitions
        WHERE iwwf_id IN ({placeholders})
        ORDER BY annee, iwwf_id
        """,
        codes,
    ).fetchall()

    entry_rows = conn.execute(
        f"""
        SELECT
            c.annee AS year,
            c.iwwf_id AS competition_code,
            e.rider_id,
            e.categorie,
            r.prenom,
            r.nom
        FROM entries e
        JOIN competitions c ON c.id = e.competition_id
        JOIN riders r ON r.id = e.rider_id
        WHERE c.iwwf_id IN ({placeholders})
        ORDER BY c.annee, c.iwwf_id, e.rider_id
        """,
        codes,
    ).fetchall()

    conn.close()

    metadata = {
        str(row["iwwf_id"]): {
            "Year": (int(row["annee"]) if row["annee"] is not None else int(str(row["iwwf_id"])[:2]) + 2000),
            "CompetitionName": row["nom"] or "",
            "Level": row["niveau"] or "",
        }
        for row in competition_rows
    }

    entries_by_code: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in entry_rows:
        if not is_u21(row["categorie"]):
            continue
        code = str(row["competition_code"])
        identity = f"RID:{row['rider_id']}"
        entries_by_code[code][identity] = {
            "Name": f"{row['prenom'] or ''} {row['nom'] or ''}".strip(),
            "CategoryRaw": row["categorie"] or "",
        }

    html_by_code: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    scanned_files: dict[str, list[str]] = defaultdict(list)

    for code in codes:
        folder = raw_root / code
        if not folder.is_dir():
            continue

        html_files = ([folder / "all_skiers_list.html"] if (folder / "all_skiers_list.html").is_file() else []) + sorted(folder.glob("21_*_results.html"))
        for path in html_files:
            scanned_files[code].append(str(path.relative_to(root)))
            for person in parse_u21_from_html(path):
                identity = (
                    f"IWWF:{person['SkierId']}"
                    if person["SkierId"]
                    else f"NAME:{normalize(person['Name'])}"
                )
                html_by_code[code].setdefault(identity, person)

    summary_rows: list[dict[str, object]] = []
    individual_rows: list[dict[str, object]] = []
    yearly_union: dict[int, set[str]] = defaultdict(set)

    for code in codes:
        meta = metadata.get(code, {})
        year = int(meta.get("Year") or int(code[:2]) + 2000)

        db_people = entries_by_code[code]
        html_people = html_by_code[code]

        # Pour le total annuel, priorité aux identifiants IWWF bruts ; à défaut,
        # nom normalisé. Les IDs SQLite et IWWF ne sont pas fusionnés ici.
        # On calcule donc aussi séparément les deux sources.
        for identity in html_people:
            yearly_union[year].add(identity)

        source_status = (
            "DB_ET_HTML"
            if db_people and html_people
            else "DB_SEUL"
            if db_people
            else "HTML_SEUL"
            if html_people
            else "AUCUN_U21"
        )

        summary_rows.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionName": meta.get("CompetitionName", ""),
                "Level": meta.get("Level", ""),
                "RawFolderExists": int((raw_root / code).is_dir()),
                "HtmlFilesScanned": len(scanned_files[code]),
                "U21Entries": len(db_people),
                "U21RawHtml": len(html_people),
                "SourceStatus": source_status,
                "FilesScanned": " | ".join(scanned_files[code]),
            }
        )

        for identity, person in html_people.items():
            individual_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "CompetitionName": meta.get("CompetitionName", ""),
                    "IdentityKey": identity,
                    "SkierId": person["SkierId"],
                    "Name": person["Name"],
                    "CategoryRaw": person["CategoryRaw"],
                    "SourceFile": person["SourceFile"],
                }
            )

    lines: list[str] = []
    lines.append("AUDIT U21 — CODES HISTORIQUES EXPLICITES 2017-2022")
    lines.append("=" * 90)
    lines.append("")
    lines.append("1. PÉRIMÈTRE")
    lines.append("-" * 90)
    lines.append(
        "Les codes sont ceux des anciens scripts de trajectoire, sans filtre "
        "sur competitions.niveau."
    )
    lines.append("Codes résolus : " + ", ".join(codes))

    lines.append("")
    lines.append("2. RÉSULTATS PAR COMPÉTITION")
    lines.append("-" * 90)
    for row in sorted(summary_rows, key=lambda item: (item["Year"], item["CompetitionCode"])):
        lines.append(
            f"{row['Year']} — {row['CompetitionCode']} — "
            f"{row['CompetitionName'] or 'nom absent'} : "
            f"niveau={row['Level'] or 'absent'} ; "
            f"U21 entries={row['U21Entries']} ; "
            f"U21 HTML={row['U21RawHtml']} ; "
            f"statut={row['SourceStatus']}."
        )

    lines.append("")
    lines.append("3. EFFECTIFS ANNUELS U21 DANS LES FICHIERS BRUTS")
    lines.append("-" * 90)
    lines.append("Année | U21 HTML distincts | ancien export | concordance")
    for year in range(2017, 2023):
        raw_count = len(yearly_union[year])
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
    lines.append("4. CONCLUSION AUTOMATIQUE")
    lines.append("-" * 90)

    years_with_u21 = [
        year for year in range(2017, 2023)
        if yearly_union[year]
    ]
    if years_with_u21:
        lines.append(
            "Des U21 historiques sont retrouvés dans les fichiers bruts pour : "
            + ", ".join(str(year) for year in years_with_u21)
            + "."
        )
    else:
        lines.append(
            "Aucun U21 historique n'est retrouvé, même après suppression du filtre niveau."
        )

    omitted_codes = [
        row for row in summary_rows
        if row["Level"] != "championnat_france"
        and (int(row["U21Entries"]) > 0 or int(row["U21RawHtml"]) > 0)
    ]
    if omitted_codes:
        lines.append(
            "Le filtre niveau=championnat_france excluait bien des compétitions "
            "contenant des U21."
        )

    matched_years = [
        year for year in range(2018, 2023)
        if year in old_counts
        and len(yearly_union[year]) == old_counts[year]
    ]
    if matched_years:
        lines.append(
            "Les fichiers bruts reproduisent l'ancien export pour : "
            + ", ".join(str(year) for year in matched_years)
            + "."
        )

    lines.append("")
    lines.append("FIN DE L'AUDIT")

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "audit_u21_codes_explicites_2017_2022.csv",
        summary_rows,
        [
            "Year",
            "CompetitionCode",
            "CompetitionName",
            "Level",
            "RawFolderExists",
            "HtmlFilesScanned",
            "U21Entries",
            "U21RawHtml",
            "SourceStatus",
            "FilesScanned",
        ],
    )
    write_csv(
        processed / "audit_u21_individus_codes_explicites_2017_2022.csv",
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

    output = exports / "audit_u21_codes_explicites_2017_2022.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 90)
    print("AUDIT U21 SUR CODES EXPLICITES TERMINE")
    print("=" * 90)
    print(f"Codes inspectés : {len(codes)}")
    print(f"Lignes individuelles HTML : {len(individual_rows)}")
    print(f"Rapport : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
