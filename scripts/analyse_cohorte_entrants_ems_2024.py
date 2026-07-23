"""Analyse la rétention en 2025 des entrants observés en 2024."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    ROOT
    / "data/processed"
    / "ems_competiteurs_annee_sexe_age_2023_2025.csv"
)

SUMMARY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_cohorte_entrants_2024_retention_2025.csv"
)

DETAIL_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_cohorte_entrants_2024_detail.csv"
)


AGE_ORDER = {
    "RELEVES": 1,
    "JUNIOR": 2,
    "U21": 3,
    "OPEN": 4,
    "SENIOR": 5,
    "UNKNOWN": 9,
}

INTENSITY_ORDER = {
    "1_COMPETITION": 1,
    "2_COMPETITIONS": 2,
    "3_4_COMPETITIONS": 3,
    "5_PLUS_COMPETITIONS": 4,
}


def read_csv(
    path: Path,
) -> list[dict[str, str]]:
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


def as_int(
    value: Any,
) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def percent(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        100 * numerator / denominator,
        1,
    )


def intensity_band(
    competitions: int,
) -> str:
    if competitions <= 1:
        return "1_COMPETITION"

    if competitions == 2:
        return "2_COMPETITIONS"

    if competitions <= 4:
        return "3_4_COMPETITIONS"

    return "5_PLUS_COMPETITIONS"


def group_value(
    row: dict[str, Any],
    dimension: str,
) -> str:
    if dimension == "ALL":
        return "ALL"

    if dimension == "SEX":
        return str(row["Sex"])

    if dimension == "AGE_BAND":
        return str(row["AgeBand"])

    if dimension == "INTENSITY":
        return str(row["IntensityBand"])

    if dimension == "SEX_X_AGE_BAND":
        return (
            f"{row['Sex']}|"
            f"{row['AgeBand']}"
        )

    raise ValueError(
        f"Dimension inconnue : {dimension}"
    )


def group_sort_key(
    dimension: str,
    group: str,
) -> tuple[Any, ...]:
    if dimension == "ALL":
        return (0,)

    if dimension == "SEX":
        return (
            {
                "F": 1,
                "M": 2,
                "UNKNOWN": 9,
            }.get(group, 9),
        )

    if dimension == "AGE_BAND":
        return (
            AGE_ORDER.get(
                group,
                9,
            ),
        )

    if dimension == "INTENSITY":
        return (
            INTENSITY_ORDER.get(
                group,
                9,
            ),
        )

    if dimension == "SEX_X_AGE_BAND":
        sex, _, population = (
            group.partition("|")
        )

        return (
            {
                "F": 1,
                "M": 2,
                "UNKNOWN": 9,
            }.get(sex, 9),
            AGE_ORDER.get(
                population,
                9,
            ),
        )

    return (9, group)


def main() -> None:
    rows = read_csv(
        SOURCE_FILE
    )

    year_maps: dict[
        int,
        dict[str, dict[str, str]],
    ] = {
        2023: {},
        2024: {},
        2025: {},
    }

    for row in rows:
        year = as_int(
            row["Year"]
        )

        year_maps[year][
            row["AthleteKey"]
        ] = row

    athletes_2023 = set(
        year_maps[2023]
    )

    athletes_2025 = set(
        year_maps[2025]
    )

    entrants: list[
        dict[str, Any]
    ] = []

    for athlete_key, row in (
        year_maps[2024].items()
    ):
        if athlete_key in athletes_2023:
            continue

        competitions = as_int(
            row["Competitions"]
        )

        entrants.append(
            {
                "AthleteKey": athlete_key,
                "Name": row["Name"],
                "Sex": row["Sex"],
                "Age": row["Age"],
                "AgeBand": row["AgeBand"],
                "Competitions2024": (
                    competitions
                ),
                "IntensityBand": (
                    intensity_band(
                        competitions
                    )
                ),
                "Present2025": int(
                    athlete_key
                    in athletes_2025
                ),
            }
        )

    dimensions = (
        "ALL",
        "SEX",
        "AGE_BAND",
        "INTENSITY",
        "SEX_X_AGE_BAND",
    )

    summary_rows: list[
        dict[str, Any]
    ] = []

    for dimension in dimensions:
        groups: dict[
            str,
            list[dict[str, Any]],
        ] = defaultdict(list)

        for row in entrants:
            groups[
                group_value(
                    row,
                    dimension,
                )
            ].append(row)

        for group in sorted(
            groups,
            key=lambda value: (
                group_sort_key(
                    dimension,
                    value,
                )
            ),
        ):
            selected = groups[group]

            retained = sum(
                int(
                    row["Present2025"]
                )
                for row in selected
            )

            summary_rows.append(
                {
                    "Dimension": dimension,
                    "Group": group,
                    "Entrants2024": len(
                        selected
                    ),
                    "Present2025": retained,
                    "Absent2025": (
                        len(selected)
                        - retained
                    ),
                    "RetentionRatePercent": (
                        percent(
                            retained,
                            len(selected),
                        )
                    ),
                    "MeanCompetitions2024": (
                        round(
                            sum(
                                int(
                                    row[
                                        "Competitions2024"
                                    ]
                                )
                                for row
                                in selected
                            )
                            / len(selected),
                            2,
                        )
                    ),
                }
            )

    entrants.sort(
        key=lambda row: (
            -int(row["Present2025"]),
            AGE_ORDER.get(
                str(row["AgeBand"]),
                9,
            ),
            str(row["Sex"]),
            str(row["Name"]),
        )
    )

    write_csv(
        SUMMARY_OUTPUT,
        summary_rows,
    )

    write_csv(
        DETAIL_OUTPUT,
        entrants,
    )

    print("=" * 110)
    print(
        "FIDÉLISATION DES ENTRANTS "
        "OBSERVÉS EN 2024"
    )
    print("=" * 110)

    overall = next(
        row
        for row in summary_rows
        if row["Dimension"] == "ALL"
    )

    print(
        "Entrants observés en 2024 :",
        overall["Entrants2024"],
    )

    print(
        "Encore présents en 2025   :",
        overall["Present2025"],
    )

    print(
        "Taux de rétention         :",
        f"{overall['RetentionRatePercent']}%",
    )

    for dimension, title in (
        (
            "INTENSITY",
            "RÉTENTION SELON L'ACTIVITÉ 2024",
        ),
        (
            "AGE_BAND",
            "RÉTENTION SELON LA POPULATION D'ÂGE",
        ),
        (
            "SEX",
            "RÉTENTION SELON LE SEXE",
        ),
        (
            "SEX_X_AGE_BAND",
            "RÉTENTION SELON LE SEXE ET L'ÂGE",
        ),
    ):
        print()
        print(title)
        print("-" * 85)

        selected_rows = [
            row
            for row in summary_rows
            if row["Dimension"]
            == dimension
        ]

        print(
            f"{'Groupe':<24}"
            f"{'Entrants':>10}"
            f"{'Maintenus':>11}"
            f"{'Sortants':>10}"
            f"{'Rétention':>12}"
            f"{'Moy. compét.':>14}"
        )
        print("-" * 83)

        for row in selected_rows:
            print(
                f"{row['Group']:<24}"
                f"{row['Entrants2024']:>10}"
                f"{row['Present2025']:>11}"
                f"{row['Absent2025']:>10}"
                f"{float(row['RetentionRatePercent']):>11.1f}%"
                f"{float(row['MeanCompetitions2024']):>14.2f}"
            )

    print()
    print("Synthèse :", SUMMARY_OUTPUT)
    print("Détail   :", DETAIL_OUTPUT)


if __name__ == "__main__":
    main()