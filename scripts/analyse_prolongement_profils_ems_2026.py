"""Mesure le prolongement provisoire en 2026 des profils EMS 2023-2025."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PANEL_FILE = (
    ROOT
    / "data/processed"
    / "ems_panel_competiteurs_francais_2023_2025.csv"
)

SOURCE_2026 = (
    ROOT
    / "data/processed"
    / "ems_participations_france_waterski_2026.csv"
)

SUMMARY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_prolongement_profils_2026_provisoire.csv"
)

DETAIL_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_sportifs_2025_presence_2026_provisoire.csv"
)

EXTRACTION_DATE = "2026-07-23"


COLUMN_CANDIDATES = {
    "athlete_key": (
        "AthleteKey",
        "athlete_key",
    ),
    "name": (
        "Name",
        "AthleteName",
        "Participant",
        "Nom",
        "name",
    ),
    "country": (
        "Country",
        "Nation",
        "country",
        "nation",
    ),
    "yob": (
        "YOB",
        "YearOfBirth",
        "BirthYear",
        "annee_naissance",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        return

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def find_column(
    columns: list[str],
    logical_name: str,
    required: bool = True,
) -> str | None:
    candidates = COLUMN_CANDIDATES[
        logical_name
    ]

    for candidate in candidates:
        if candidate in columns:
            return candidate

    lower_lookup = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:
        actual = lower_lookup.get(
            candidate.lower()
        )

        if actual:
            return actual

    if required:
        raise RuntimeError(
            f"Colonne introuvable pour "
            f"{logical_name} : {columns}"
        )

    return None


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.upper()
    text = re.sub(
        r"[^A-Z0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def parse_key(
    value: Any,
) -> tuple[str, str, str]:
    parts = str(value or "").split("|")

    if len(parts) < 3:
        return "", "", ""

    return (
        parts[0].strip().upper(),
        parts[1].strip(),
        "|".join(parts[2:]).strip(),
    )


def canonical_key(
    row: dict[str, str],
    columns: dict[str, str | None],
) -> tuple[str, str]:
    raw_key = str(
        row.get(
            columns["athlete_key"] or "",
            "",
        )
    ).strip()

    key_country, key_yob, key_name = (
        parse_key(raw_key)
    )

    country = str(
        row.get(
            columns["country"] or "",
            "",
        )
    ).strip().upper() or key_country

    yob = str(
        row.get(
            columns["yob"] or "",
            "",
        )
    ).strip() or key_yob

    name = str(
        row.get(
            columns["name"] or "",
            "",
        )
    ).strip() or key_name

    return (
        f"{country}|{yob}|"
        f"{normalize_text(name)}",
        name,
    )


def percent(
    numerator: int,
    denominator: int,
) -> float | str:
    if denominator == 0:
        return ""

    return round(
        100 * numerator / denominator,
        1,
    )


def main() -> None:
    panel = read_csv(
        PANEL_FILE
    )

    rows_2026 = read_csv(
        SOURCE_2026
    )

    if not rows_2026:
        raise RuntimeError(
            f"Fichier vide : {SOURCE_2026}"
        )

    columns_list = list(
        rows_2026[0].keys()
    )

    columns = {
        "athlete_key": find_column(
            columns_list,
            "athlete_key",
            required=False,
        ),
        "name": find_column(
            columns_list,
            "name",
        ),
        "country": find_column(
            columns_list,
            "country",
        ),
        "yob": find_column(
            columns_list,
            "yob",
            required=False,
        ),
    }

    athletes_2026: set[str] = set()

    for row in rows_2026:
        athlete_key, _ = canonical_key(
            row,
            columns,
        )

        if not athlete_key.startswith(
            "FRA|"
        ):
            continue

        athletes_2026.add(
            athlete_key
        )

    profile_groups: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in panel:
        profile_groups[
            row["FidelityProfile"]
        ].append(row)

    summary_rows: list[
        dict[str, Any]
    ] = []

    profile_order = (
        "CORE_3_YEARS",
        "TWO_YEARS_2023_2024",
        "TWO_YEARS_2024_2025",
        "RETURN_AFTER_GAP",
        "ONE_SEASON_2023",
        "ONE_SEASON_2024",
        "ONE_SEASON_2025",
    )

    for profile in profile_order:
        group = profile_groups.get(
            profile,
            [],
        )

        present_2026 = [
            row
            for row in group
            if row["AthleteKey"]
            in athletes_2026
        ]

        summary_rows.append(
            {
                "ExtractionDate": (
                    EXTRACTION_DATE
                ),
                "FidelityProfile": profile,
                "Athletes2023To2025": (
                    len(group)
                ),
                "Present2026Provisional": (
                    len(present_2026)
                ),
                "ObservedContinuationPercent": (
                    percent(
                        len(present_2026),
                        len(group),
                    )
                ),
            }
        )

    active_2025 = [
        row
        for row in panel
        if row["Present2025"] == "1"
    ]

    detail_rows: list[
        dict[str, Any]
    ] = []

    for row in active_2025:
        detail_rows.append(
            {
                "ExtractionDate": (
                    EXTRACTION_DATE
                ),
                "AthleteKey": (
                    row["AthleteKey"]
                ),
                "Name": row["Name"],
                "FidelityProfile": (
                    row["FidelityProfile"]
                ),
                "Competitions2025": (
                    row["Competitions2025"]
                ),
                "Present2026Provisional": int(
                    row["AthleteKey"]
                    in athletes_2026
                ),
            }
        )

    detail_rows.sort(
        key=lambda row: (
            -int(
                row[
                    "Present2026Provisional"
                ]
            ),
            str(row["FidelityProfile"]),
            str(row["Name"]),
        )
    )

    write_csv(
        SUMMARY_OUTPUT,
        summary_rows,
    )

    write_csv(
        DETAIL_OUTPUT,
        detail_rows,
    )

    active_2025_present_2026 = sum(
        1
        for row in active_2025
        if row["AthleteKey"]
        in athletes_2026
    )

    print("=" * 120)
    print(
        "PROLONGEMENT PROVISOIRE EN 2026 "
        "DES PROFILS 2023-2025"
    )
    print("=" * 120)

    print(
        "Date d'observation :",
        EXTRACTION_DATE,
    )

    print(
        "Compétiteurs français 2026 :",
        len(athletes_2026),
    )

    print()
    print(
        f"{'Profil':<29}"
        f"{'Effectif':>10}"
        f"{'Présents 2026':>16}"
        f"{'Taux minimal':>15}"
    )
    print("-" * 70)

    for row in summary_rows:
        rate = row[
            "ObservedContinuationPercent"
        ]

        rate_text = (
            f"{float(rate):.1f}%"
            if rate != ""
            else ""
        )

        print(
            f"{row['FidelityProfile']:<29}"
            f"{row['Athletes2023To2025']:>10}"
            f"{row['Present2026Provisional']:>16}"
            f"{rate_text:>15}"
        )

    print()
    print("COHORTE ACTIVE EN 2025")
    print("=" * 120)

    print(
        "Sportifs actifs en 2025 :",
        len(active_2025),
    )

    print(
        "Déjà visibles en 2026  :",
        active_2025_present_2026,
    )

    print(
        "Taux minimal observé   :",
        f"{percent(
            active_2025_present_2026,
            len(active_2025),
        )}%",
    )

    one_season_2025 = [
        row
        for row in panel
        if row["FidelityProfile"]
        == "ONE_SEASON_2025"
    ]

    one_season_2025_present = [
        row
        for row in one_season_2025
        if row["AthleteKey"]
        in athletes_2026
    ]

    print()
    print("ENTRANTS OBSERVÉS UNIQUEMENT EN 2025")
    print("=" * 120)

    print(
        "Effectif 2025           :",
        len(one_season_2025),
    )

    print(
        "Déjà présents en 2026   :",
        len(
            one_season_2025_present
        ),
    )

    print(
        "Continuation minimale   :",
        f"{percent(
            len(one_season_2025_present),
            len(one_season_2025),
        )}%",
    )

    print()
    print("Synthèse :", SUMMARY_OUTPUT)
    print("Détail   :", DETAIL_OUTPUT)


if __name__ == "__main__":
    main()