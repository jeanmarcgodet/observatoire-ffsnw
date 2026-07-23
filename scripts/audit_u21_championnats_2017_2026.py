"""Audite les catégories U21 des Championnats de France 2017-2026.

But
---
Vérifier pourquoi l'analyse longitudinale récente ne détecte des sorties U21
qu'à partir de 2023, alors que des exports antérieurs couvrent 2017-2023.

Le script :
1. inventorie tous les libellés bruts de catégorie par année ;
2. applique plusieurs règles de détection U21 ;
3. compare les effectifs détectés avec participation_categories_2017_2026.csv ;
4. liste les sportifs potentiellement U21 non reconnus par la règle actuelle.

Aucune donnée existante n'est modifiée.

Sorties
-------
data/processed/audit_categories_championnats_2017_2026.csv
data/processed/audit_u21_sportifs_non_reconnus_2017_2026.csv
data/exports/audit_u21_championnats_2017_2026.txt
"""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


START_YEAR = 2017
END_YEAR = 2026


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.upper())
    return text.strip()


def current_rule(category_raw: str | None) -> bool:
    category = normalize(category_raw)
    return bool(
        re.search(r"(^|[^0-9])U?21([^0-9]|$)", category)
        or re.match(r"^-21(?:\s|$)", category)
        or "UNDER 21" in category
    )


def broad_u21_rule(category_raw: str | None) -> bool:
    """Règle d'audit volontairement large, non destinée à la production."""
    category = normalize(category_raw)
    patterns = (
        r"(^|[^0-9])U[\s_-]?21([^0-9]|$)",
        r"(^|[^0-9])-?21([^0-9]|$)",
        r"UNDER[\s_-]?21",
        r"MOINS[\s_-]?DE[\s_-]?21",
        r"21[\s_-]?ANS",
        r"ESPOIR",
    )
    return any(re.search(pattern, category) for pattern in patterns)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def read_old_u21_counts(path: Path) -> dict[int, int]:
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


def main() -> None:
    root = repo_root()
    db_path = root / "data/observatoire.db"
    old_export = root / "data/exports/participation_categories_2017_2026.csv"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            c.annee AS year,
            c.iwwf_id AS competition_code,
            c.nom AS competition_name,
            c.niveau AS competition_level,
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
        ORDER BY c.annee, c.iwwf_id, e.categorie, e.rider_id
        """,
        (START_YEAR, END_YEAR),
    ).fetchall()

    conn.close()

    raw_counts: Counter[tuple[int, str]] = Counter()
    raw_riders: dict[tuple[int, str], set[int]] = defaultdict(set)
    current_u21_by_year: dict[int, set[int]] = defaultdict(set)
    broad_u21_by_year: dict[int, set[int]] = defaultdict(set)

    suspicious_rows: list[dict[str, object]] = []

    for row in rows:
        year = int(row["year"])
        category = (row["category"] or "").strip()
        rider_id = int(row["rider_id"])
        key = (year, category)

        raw_counts[key] += 1
        raw_riders[key].add(rider_id)

        current = current_rule(category)
        broad = broad_u21_rule(category)

        if current:
            current_u21_by_year[year].add(rider_id)
        if broad:
            broad_u21_by_year[year].add(rider_id)

        age = ""
        if row["yob"] is not None:
            age = year - int(row["yob"])

        # Audit des sportifs d'âge compatible U21 mais non reconnus.
        if not current and isinstance(age, int) and 15 <= age <= 21:
            suspicious_rows.append({
                "Year": year,
                "CompetitionCode": row["competition_code"],
                "CompetitionName": row["competition_name"],
                "RiderId": rider_id,
                "Name": f"{row['firstname'] or ''} {row['surname'] or ''}".strip(),
                "Sex": row["sex"] or "",
                "YOB": row["yob"] or "",
                "Age": age,
                "CategoryRaw": category,
                "BroadRuleMatches": int(broad),
                "Reason": "AGE_15_21_NON_RECONNU_PAR_REGLE_U21",
            })

    audit_rows: list[dict[str, object]] = []
    for (year, category), entry_count in sorted(
        raw_counts.items(),
        key=lambda item: (item[0][0], normalize(item[0][1])),
    ):
        audit_rows.append({
            "Year": year,
            "CategoryRaw": category,
            "NormalizedCategory": normalize(category),
            "Entries": entry_count,
            "DistinctRiders": len(raw_riders[(year, category)]),
            "CurrentRuleU21": int(current_rule(category)),
            "BroadAuditRuleU21": int(broad_u21_rule(category)),
        })

    old_counts = read_old_u21_counts(old_export)

    lines: list[str] = []
    lines.append("AUDIT DES CATÉGORIES U21 — CHAMPIONNATS DE FRANCE 2017-2026")
    lines.append("=" * 86)
    lines.append("")
    lines.append("1. COMPARAISON DES EFFECTIFS U21 PAR ANNÉE")
    lines.append("-" * 86)
    lines.append(
        "Année | règle actuelle | règle large d'audit | ancien export participation_categories"
    )

    for year in range(START_YEAR, END_YEAR + 1):
        lines.append(
            f"{year} | {len(current_u21_by_year[year])} | "
            f"{len(broad_u21_by_year[year])} | {old_counts.get(year, 'n.d.')}"
        )

    lines.append("")
    lines.append("2. LIBELLÉS BRUTS CONSIDÉRÉS U21 PAR LA RÈGLE ACTUELLE")
    lines.append("-" * 86)
    for row in audit_rows:
        if int(row["CurrentRuleU21"]) == 1:
            lines.append(
                f"{row['Year']} — {row['CategoryRaw']!r} : "
                f"{row['DistinctRiders']} sportifs distincts."
            )

    lines.append("")
    lines.append("3. LIBELLÉS DÉTECTÉS PAR LA RÈGLE LARGE MAIS PAS PAR LA RÈGLE ACTUELLE")
    lines.append("-" * 86)
    missed_labels = [
        row for row in audit_rows
        if int(row["BroadAuditRuleU21"]) == 1
        and int(row["CurrentRuleU21"]) == 0
    ]
    if not missed_labels:
        lines.append("Aucun libellé supplémentaire détecté.")
    else:
        for row in missed_labels:
            lines.append(
                f"{row['Year']} — {row['CategoryRaw']!r} : "
                f"{row['DistinctRiders']} sportifs distincts."
            )

    lines.append("")
    lines.append("4. SPORTIFS ÂGÉS DE 15 À 21 ANS NON RECONNUS COMME U21")
    lines.append("-" * 86)
    by_year_suspicious: Counter[int] = Counter(
        int(row["Year"]) for row in suspicious_rows
    )
    for year in range(START_YEAR, END_YEAR + 1):
        lines.append(f"{year} : {by_year_suspicious[year]} lignes à examiner.")

    lines.append("")
    lines.append("5. CONCLUSION AUTOMATIQUE")
    lines.append("-" * 86)

    discrepancies = [
        year for year in range(START_YEAR, END_YEAR + 1)
        if old_counts.get(year) is not None
        and old_counts.get(year) != len(current_u21_by_year[year])
    ]

    if discrepancies:
        lines.append(
            "Écart détecté avec l'ancien export pour : "
            + ", ".join(str(year) for year in discrepancies)
            + "."
        )
        lines.append(
            "La reconstruction U21→Open ne doit pas être interprétée avant "
            "correction ou explication de ces écarts."
        )
    else:
        lines.append(
            "Aucun écart numérique détecté avec l'ancien export disponible."
        )

    lines.append("")
    lines.append("FIN DE L'AUDIT")

    processed = root / "data/processed"
    exports = root / "data/exports"

    write_csv(
        processed / "audit_categories_championnats_2017_2026.csv",
        audit_rows,
        [
            "Year",
            "CategoryRaw",
            "NormalizedCategory",
            "Entries",
            "DistinctRiders",
            "CurrentRuleU21",
            "BroadAuditRuleU21",
        ],
    )
    write_csv(
        processed / "audit_u21_sportifs_non_reconnus_2017_2026.csv",
        suspicious_rows,
        [
            "Year",
            "CompetitionCode",
            "CompetitionName",
            "RiderId",
            "Name",
            "Sex",
            "YOB",
            "Age",
            "CategoryRaw",
            "BroadRuleMatches",
            "Reason",
        ],
    )

    output = exports / "audit_u21_championnats_2017_2026.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    print("=" * 88)
    print("AUDIT U21 TERMINE")
    print("=" * 88)
    print(f"Libellés audités : {len(audit_rows)}")
    print(f"Lignes d'âge 15-21 non reconnues : {len(suspicious_rows)}")
    print(f"Rapport : {output}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
