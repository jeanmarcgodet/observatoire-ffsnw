"""Réconcilie les catégories U21 entre inscriptions et résultats, 2017-2026.

Objectif
--------
Déterminer si les catégories U21 absentes de la table `entries` avant 2023
sont présentes dans `result_classifications`, et identifier la source à retenir
pour reconstruire la filière U21 -> Open.

Le script ne modifie aucune donnée existante.

Entrées
-------
- data/observatoire.db
- data/reference/rider_identity_map.csv
- data/exports/participation_categories_2017_2026.csv

Sorties
-------
- data/processed/audit_u21_entries_vs_resultats_2017_2026.csv
- data/processed/audit_u21_individus_entries_vs_resultats_2017_2026.csv
- data/exports/audit_u21_sources_2017_2026.txt
"""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path


START_YEAR = 2017
END_YEAR = 2026
YEARS = range(START_YEAR, END_YEAR + 1)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def is_u21(category_raw: str | None) -> bool:
    category = normalize(category_raw)
    return bool(
        re.search(r"(^|[^0-9])U?21([^0-9]|$)", category)
        or re.match(r"^-21(?:\s|$)", category)
        or "UNDER 21" in category
    )


def read_alias_map(path: Path) -> dict[int, int]:
    aliases: dict[int, int] = {}
    if not path.exists():
        return aliases

    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            try:
                alias_id = int((row.get("alias_rider_id") or "").strip())
                canonical_id = int((row.get("canonical_rider_id") or "").strip())
            except ValueError:
                continue
            aliases[alias_id] = canonical_id

    return aliases


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


def main() -> None:
    root = repo_root()
    db_path = root / "data/observatoire.db"
    alias_map = read_alias_map(root / "data/reference/rider_identity_map.csv")
    old_counts = read_old_counts(
        root / "data/exports/participation_categories_2017_2026.csv"
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    entry_rows = conn.execute(
        """
        SELECT
            c.annee AS year,
            c.iwwf_id AS competition_code,
            c.nom AS competition_name,
            e.rider_id AS rider_id,
            e.categorie AS category,
            r.prenom AS firstname,
            r.nom AS surname,
            r.sexe AS sex,
            r.annee_naissance AS yob
        FROM entries e
        JOIN competitions c ON c.id = e.competition_id
        JOIN riders r ON r.id = e.rider_id
        WHERE c.annee BETWEEN ? AND ?
          AND c.niveau = 'championnat_france'
        """,
        (START_YEAR, END_YEAR),
    ).fetchall()

    result_rows = conn.execute(
        """
        SELECT
            c.annee AS year,
            c.iwwf_id AS competition_code,
            c.nom AS competition_name,
            res.rider_id AS rider_id,
            rc.categorie AS category,
            rc.classement AS classification_label,
            rc.sexe AS classification_sex,
            r.prenom AS firstname,
            r.nom AS surname,
            r.sexe AS rider_sex,
            r.annee_naissance AS yob
        FROM result_classifications rc
        JOIN results res ON res.id = rc.result_id
        JOIN competitions c ON c.id = res.competition_id
        JOIN riders r ON r.id = res.rider_id
        WHERE c.annee BETWEEN ? AND ?
          AND c.niveau = 'championnat_france'
        """,
        (START_YEAR, END_YEAR),
    ).fetchall()

    conn.close()

    entries_u21: dict[int, set[int]] = defaultdict(set)
    results_u21: dict[int, set[int]] = defaultdict(set)
    entry_categories_by_person: dict[tuple[int, int], set[str]] = defaultdict(set)
    result_categories_by_person: dict[tuple[int, int], set[str]] = defaultdict(set)
    person_meta: dict[tuple[int, int], dict[str, object]] = {}

    for row in entry_rows:
        year = int(row["year"])
        rider_id = int(row["rider_id"])
        canonical_id = alias_map.get(rider_id, rider_id)
        key = (year, canonical_id)
        category = (row["category"] or "").strip()
        entry_categories_by_person[key].add(category)

        person_meta.setdefault(
            key,
            {
                "Name": f"{row['firstname'] or ''} {row['surname'] or ''}".strip(),
                "Sex": row["sex"] or "",
                "YOB": row["yob"] or "",
            },
        )

        if is_u21(category):
            entries_u21[year].add(canonical_id)

    for row in result_rows:
        year = int(row["year"])
        rider_id = int(row["rider_id"])
        canonical_id = alias_map.get(rider_id, rider_id)
        key = (year, canonical_id)
        category = (row["category"] or "").strip()
        result_categories_by_person[key].add(category)

        person_meta.setdefault(
            key,
            {
                "Name": f"{row['firstname'] or ''} {row['surname'] or ''}".strip(),
                "Sex": row["rider_sex"] or row["classification_sex"] or "",
                "YOB": row["yob"] or "",
            },
        )

        if is_u21(category):
            results_u21[year].add(canonical_id)

    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []

    for year in YEARS:
        entry_set = entries_u21[year]
        result_set = results_u21[year]
        shared = entry_set & result_set
        entries_only = entry_set - result_set
        results_only = result_set - entry_set
        union = entry_set | result_set

        summary_rows.append(
            {
                "Year": year,
                "U21Entries": len(entry_set),
                "U21Results": len(result_set),
                "Shared": len(shared),
                "EntriesOnly": len(entries_only),
                "ResultsOnly": len(results_only),
                "Union": len(union),
                "OldExportU21": old_counts.get(year, ""),
                "ResultsMatchOldExport": (
                    int(len(result_set) == old_counts[year])
                    if year in old_counts
                    else ""
                ),
                "UnionMatchOldExport": (
                    int(len(union) == old_counts[year])
                    if year in old_counts
                    else ""
                ),
            }
        )

        for canonical_id in sorted(union):
            key = (year, canonical_id)
            if canonical_id in shared:
                status = "MATCH"
            elif canonical_id in entries_only:
                status = "ENTRIES_ONLY"
            else:
                status = "RESULTS_ONLY"

            meta = person_meta.get(key, {})
            detail_rows.append(
                {
                    "Year": year,
                    "CanonicalRiderId": canonical_id,
                    "Name": meta.get("Name", ""),
                    "Sex": meta.get("Sex", ""),
                    "YOB": meta.get("YOB", ""),
                    "Status": status,
                    "EntryCategories": " | ".join(
                        sorted(entry_categories_by_person.get(key, set()))
                    ),
                    "ResultCategories": " | ".join(
                        sorted(result_categories_by_person.get(key, set()))
                    ),
                }
            )

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "audit_u21_entries_vs_resultats_2017_2026.csv",
        summary_rows,
        [
            "Year",
            "U21Entries",
            "U21Results",
            "Shared",
            "EntriesOnly",
            "ResultsOnly",
            "Union",
            "OldExportU21",
            "ResultsMatchOldExport",
            "UnionMatchOldExport",
        ],
    )

    write_csv(
        processed / "audit_u21_individus_entries_vs_resultats_2017_2026.csv",
        detail_rows,
        [
            "Year",
            "CanonicalRiderId",
            "Name",
            "Sex",
            "YOB",
            "Status",
            "EntryCategories",
            "ResultCategories",
        ],
    )

    lines: list[str] = []
    lines.append("AUDIT DES SOURCES U21 — ENTRIES VS RÉSULTATS 2017-2026")
    lines.append("=" * 88)
    lines.append("")
    lines.append(
        "Année | entries U21 | résultats U21 | communs | résultats seuls | "
        "ancien export | résultats=ancien export"
    )
    lines.append("-" * 88)

    for row in summary_rows:
        old = row["OldExportU21"] if row["OldExportU21"] != "" else "n.d."
        match = (
            row["ResultsMatchOldExport"]
            if row["ResultsMatchOldExport"] != ""
            else "n.d."
        )
        lines.append(
            f"{row['Year']} | {row['U21Entries']} | {row['U21Results']} | "
            f"{row['Shared']} | {row['ResultsOnly']} | {old} | {match}"
        )

    lines.append("")
    lines.append("INDIVIDUS U21 PRÉSENTS DANS LES RÉSULTATS MAIS ABSENTS DES ENTRIES")
    lines.append("-" * 88)

    results_only_rows = [row for row in detail_rows if row["Status"] == "RESULTS_ONLY"]
    if not results_only_rows:
        lines.append("Aucun.")
    else:
        for row in results_only_rows:
            lines.append(
                f"{row['Year']} — {row['Name']} (id {row['CanonicalRiderId']}) : "
                f"entries={row['EntryCategories'] or 'aucune'} ; "
                f"résultats={row['ResultCategories'] or 'aucune'}."
            )

    lines.append("")
    lines.append("CONCLUSION AUTOMATIQUE")
    lines.append("-" * 88)

    years_results_match = [
        int(row["Year"])
        for row in summary_rows
        if row["OldExportU21"] != ""
        and row["ResultsMatchOldExport"] == 1
    ]
    years_results_differ = [
        int(row["Year"])
        for row in summary_rows
        if row["OldExportU21"] != ""
        and row["ResultsMatchOldExport"] == 0
    ]

    if years_results_match:
        lines.append(
            "Les résultats reproduisent exactement l'ancien export pour : "
            + ", ".join(str(year) for year in years_results_match)
            + "."
        )

    if years_results_differ:
        lines.append(
            "Des écarts persistent entre résultats et ancien export pour : "
            + ", ".join(str(year) for year in years_results_differ)
            + "."
        )

    if all(
        len(entries_u21[year]) == 0 and len(results_u21[year]) > 0
        for year in range(2018, 2023)
    ):
        lines.append(
            "Pour 2018-2022, l'absence U21 provient bien de la table entries : "
            "les résultats contiennent des U21 alors que les inscriptions n'en contiennent aucun."
        )

    lines.append(
        "La reconstruction définitive devra utiliser une source harmonisée : "
        "résultats classés pour les années anciennes, puis résultats/EMS réconciliés "
        "pour les années récentes."
    )
    lines.append("")
    lines.append("FIN DE L'AUDIT")

    output = exports / "audit_u21_sources_2017_2026.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("AUDIT ENTRIES VS RESULTATS TERMINE")
    print("=" * 88)
    print(f"Rapport : {output}")
    print(f"Individus résultats seuls : {len(results_only_rows)}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
