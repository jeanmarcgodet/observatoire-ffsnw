"""Réconciliation robuste des Open du Championnat de France, 2023-2025.

Cette version corrige deux défauts de l'audit précédent :
1. les noms sont rapprochés indépendamment de l'ordre prénom/nom ;
2. la catégorie Open est lue directement dans les lignes `entries` du code
   de compétition, sans utiliser le registre annuel agrégé qui dissocie
   catégories et codes.

Rapprochement
-------------
- clé principale : sac de mots du nom + année de naissance ;
- si l'année de naissance manque d'un côté : sac de mots du nom seul,
  uniquement lorsque la correspondance est unique ;
- dernier recours : rapprochement approché sur le nom, avec même année de
  naissance lorsqu'elle est connue des deux côtés.

Sorties
-------
data/processed/audit_identites_championnat_open_2023_2025_v2.csv
data/exports/audit_identites_championnat_open_2023_2025_v2.txt
"""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


CODES = {
    2023: "23FRA018",
    2024: "24FRA027",
    2025: "25FRA206",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def bag_name(value: str | None) -> str:
    tokens = normalize(value).split()
    return " ".join(sorted(tokens))


def is_open(value: str | None) -> bool:
    category = normalize(value)
    return "OPEN" in category or bool(
        re.search(r"(^| )PRO( |$)", category)
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
        except csv.Error:
            delimiter = ";"
        return list(csv.DictReader(handle, delimiter=delimiter))


def first(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name])
    return ""


def parse_yob(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def ems_name(row: dict[str, str]) -> str:
    name = first(row, "AthleteName", "RiderName", "Name", "name").strip()
    if name:
        return name

    athlete_key = first(row, "AthleteKey", "athlete_key", "RiderKey")
    parts = athlete_key.split("|", 2)
    return parts[2].strip() if len(parts) == 3 else athlete_key.strip()


def ems_yob(row: dict[str, str]) -> str:
    value = first(
        row,
        "YOB",
        "yob",
        "YearOfBirth",
        "BirthYear",
    )
    if value:
        return parse_yob(value)

    athlete_key = first(row, "AthleteKey", "athlete_key", "RiderKey")
    parts = athlete_key.split("|", 2)
    return parse_yob(parts[1]) if len(parts) == 3 else ""


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def load_db_open_entries(
    conn: sqlite3.Connection,
    code: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            e.rider_id AS rider_id,
            e.categorie AS category,
            r.prenom AS firstname,
            r.nom AS surname,
            r.annee_naissance AS yob
        FROM entries e
        JOIN competitions c ON c.id = e.competition_id
        JOIN riders r ON r.id = e.rider_id
        WHERE c.iwwf_id = ?
        ORDER BY e.rider_id
        """,
        (code,),
    ).fetchall()

    by_rider: dict[int, dict[str, object]] = {}

    for row in rows:
        category = str(row["category"] or "").strip()
        if not is_open(category):
            continue

        rider_id = int(row["rider_id"])
        name = " ".join(
            value
            for value in (row["firstname"], row["surname"])
            if value
        ).strip()
        yob = parse_yob(row["yob"])

        current = by_rider.setdefault(
            rider_id,
            {
                "RiderId": rider_id,
                "Name": name,
                "YOB": yob,
                "Categories": set(),
            },
        )
        current["Categories"].add(category)

    output: list[dict[str, object]] = []
    for row in by_rider.values():
        output.append(
            {
                "RiderId": row["RiderId"],
                "Name": row["Name"],
                "YOB": row["YOB"],
                "Categories": " | ".join(sorted(row["Categories"])),
            }
        )
    return output


def load_ems_open_entries(root: Path, year: int, code: str) -> list[dict[str, str]]:
    path = root / f"data/processed/ems_participations_france_waterski_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    by_key: dict[str, dict[str, str]] = {}

    for row in read_csv(path):
        row_code = first(
            row, "CompetitionCode", "competition_code", "Code"
        ).strip()
        category = first(row, "Category", "category", "Categorie")

        if row_code != code or not is_open(category):
            continue

        name = ems_name(row)
        yob = ems_yob(row)
        athlete_key = first(
            row, "AthleteKey", "athlete_key", "RiderKey"
        ).strip()
        country = first(
            row, "Country", "country", "Nation"
        ).strip()

        identity = athlete_key or f"{country}|{yob}|{bag_name(name)}"
        by_key.setdefault(
            identity,
            {
                "AthleteKey": athlete_key,
                "Name": name,
                "YOB": yob,
                "Country": country,
                "Category": category,
            },
        )

    return list(by_key.values())


def compatible_yob(left: str, right: str) -> bool:
    return not left or not right or left == right


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, bag_name(left), bag_name(right)).ratio()


def reconcile(
    db_rows: list[dict[str, object]],
    ems_rows: list[dict[str, str]],
) -> tuple[
    list[tuple[str, float, dict[str, object], dict[str, str]]],
    list[dict[str, object]],
    list[dict[str, str]],
]:
    matches: list[
        tuple[str, float, dict[str, object], dict[str, str]]
    ] = []
    used_db: set[int] = set()
    used_ems: set[int] = set()

    # 1. Sac de mots exact + YOB compatible.
    for db_index, db_row in enumerate(db_rows):
        candidates = [
            ems_index
            for ems_index, ems_row in enumerate(ems_rows)
            if ems_index not in used_ems
            and bag_name(str(db_row["Name"])) == bag_name(ems_row["Name"])
            and compatible_yob(str(db_row["YOB"]), ems_row["YOB"])
        ]
        if len(candidates) == 1:
            ems_index = candidates[0]
            used_db.add(db_index)
            used_ems.add(ems_index)
            match_type = (
                "SAC_MOTS_ET_YOB"
                if str(db_row["YOB"]) and ems_rows[ems_index]["YOB"]
                else "SAC_MOTS_YOB_MANQUANT"
            )
            matches.append(
                (match_type, 1.0, db_row, ems_rows[ems_index])
            )

    # 2. Nom approché, avec appariement mutuellement unique.
    proposals: list[tuple[float, int, int]] = []
    for db_index, db_row in enumerate(db_rows):
        if db_index in used_db:
            continue

        for ems_index, ems_row in enumerate(ems_rows):
            if ems_index in used_ems:
                continue
            if not compatible_yob(str(db_row["YOB"]), ems_row["YOB"]):
                continue

            score = similarity(str(db_row["Name"]), ems_row["Name"])
            if score >= 0.86:
                proposals.append((score, db_index, ems_index))

    proposals.sort(reverse=True)

    for score, db_index, ems_index in proposals:
        if db_index in used_db or ems_index in used_ems:
            continue

        competing_db = [
            item
            for item in proposals
            if item[2] == ems_index
            and item[1] not in used_db
            and abs(item[0] - score) < 0.02
        ]
        competing_ems = [
            item
            for item in proposals
            if item[1] == db_index
            and item[2] not in used_ems
            and abs(item[0] - score) < 0.02
        ]

        if len(competing_db) > 1 or len(competing_ems) > 1:
            continue

        used_db.add(db_index)
        used_ems.add(ems_index)
        matches.append(
            ("NOM_APPROCHE", round(score, 4), db_rows[db_index], ems_rows[ems_index])
        )

    db_only = [
        row for index, row in enumerate(db_rows) if index not in used_db
    ]
    ems_only = [
        row for index, row in enumerate(ems_rows) if index not in used_ems
    ]
    return matches, db_only, ems_only


def main() -> None:
    root = repo_root()
    db_path = root / "data/observatoire.db"
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    report: list[str] = []
    output_rows: list[dict[str, object]] = []

    report.append("RÉCONCILIATION ROBUSTE DES IDENTITÉS OPEN — 2023-2025")
    report.append("=" * 88)
    report.append("")
    report.append(
        "Source DB : lignes entries Open du code précis. "
        "Source EMS : participations Open approuvées du même code."
    )
    report.append("")

    for year, code in CODES.items():
        db_rows = load_db_open_entries(conn, code)
        ems_rows = load_ems_open_entries(root, year, code)
        matches, db_only, ems_only = reconcile(db_rows, ems_rows)

        report.append(
            f"{year} — {code} : DB Open={len(db_rows)} ; "
            f"EMS Open={len(ems_rows)} ; appariés={len(matches)} ; "
            f"DB seul={len(db_only)} ; EMS seul={len(ems_only)}."
        )

        approximate = [
            match for match in matches if match[0] == "NOM_APPROCHE"
        ]
        if approximate:
            report.append("       APPARIEMENTS APPROCHÉS À CONTRÔLER :")
            for match_type, score, db_row, ems_row in approximate:
                report.append(
                    f"       - {db_row['Name']} ({db_row['YOB']}) "
                    f"↔ {ems_row['Name']} ({ems_row['YOB']}) ; "
                    f"score={score}."
                )

        if db_only:
            report.append("       DB SEUL :")
            for row in db_only:
                report.append(
                    f"       - ID={row['RiderId']} ; "
                    f"{row['Name']} ; YOB={row['YOB']} ; "
                    f"catégorie={row['Categories']}."
                )

        if ems_only:
            report.append("       EMS SEUL :")
            for row in ems_only:
                report.append(
                    f"       - {row['AthleteKey']} ; "
                    f"{row['Name']} ; YOB={row['YOB']} ; "
                    f"pays={row['Country']} ; catégorie={row['Category']}."
                )

        report.append("")

        for match_type, score, db_row, ems_row in matches:
            output_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "Status": "MATCH",
                    "MatchType": match_type,
                    "Similarity": score,
                    "DBRiderId": db_row["RiderId"],
                    "DBName": db_row["Name"],
                    "DBYOB": db_row["YOB"],
                    "DBCategory": db_row["Categories"],
                    "EMSAthleteKey": ems_row["AthleteKey"],
                    "EMSName": ems_row["Name"],
                    "EMSYOB": ems_row["YOB"],
                    "EMSCountry": ems_row["Country"],
                    "EMSCategory": ems_row["Category"],
                }
            )

        for db_row in db_only:
            output_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "Status": "DB_SEUL",
                    "MatchType": "",
                    "Similarity": "",
                    "DBRiderId": db_row["RiderId"],
                    "DBName": db_row["Name"],
                    "DBYOB": db_row["YOB"],
                    "DBCategory": db_row["Categories"],
                    "EMSAthleteKey": "",
                    "EMSName": "",
                    "EMSYOB": "",
                    "EMSCountry": "",
                    "EMSCategory": "",
                }
            )

        for ems_row in ems_only:
            output_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": code,
                    "Status": "EMS_SEUL",
                    "MatchType": "",
                    "Similarity": "",
                    "DBRiderId": "",
                    "DBName": "",
                    "DBYOB": "",
                    "DBCategory": "",
                    "EMSAthleteKey": ems_row["AthleteKey"],
                    "EMSName": ems_row["Name"],
                    "EMSYOB": ems_row["YOB"],
                    "EMSCountry": ems_row["Country"],
                    "EMSCategory": ems_row["Category"],
                }
            )

    conn.close()

    report.append("INTERPRÉTATION")
    report.append("- DB_SEUL : inscription Open présente dans `entries`, absente de l'export EMS annuel.")
    report.append("- EMS_SEUL : inscription EMS approuvée absente des `entries` importées.")
    report.append("- Les lignes appariées par nom approché doivent être contrôlées visuellement.")
    report.append("")
    report.append("FIN DE L'AUDIT")

    output_csv = (
        root / "data/processed/audit_identites_championnat_open_2023_2025_v2.csv"
    )
    output_txt = (
        root / "data/exports/audit_identites_championnat_open_2023_2025_v2.txt"
    )

    write_csv(
        output_csv,
        output_rows,
        [
            "Year",
            "CompetitionCode",
            "Status",
            "MatchType",
            "Similarity",
            "DBRiderId",
            "DBName",
            "DBYOB",
            "DBCategory",
            "EMSAthleteKey",
            "EMSName",
            "EMSYOB",
            "EMSCountry",
            "EMSCategory",
        ],
    )
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text("\n".join(report), encoding="utf-8")

    print("=" * 88)
    print("RÉCONCILIATION ROBUSTE TERMINÉE")
    print("=" * 88)
    print(f"Diagnostic : {output_txt}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
