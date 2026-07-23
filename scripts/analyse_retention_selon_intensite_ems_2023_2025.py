"""Analyse la rétention selon l'intensité compétitive de la saison précédente."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
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
    / "ems_retention_selon_intensite_2023_2025.csv"
)

ACTIVITY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_activite_avant_maintien_sortie_2023_2025.csv"
)

NEWCOMER_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_retention_entrants_2024_vers_2025.csv"
)


AGE_ORDER = {
    "ALL": 0,
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


def as_int(value: Any) -> int:
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


def safe_mean(
    values: list[int],
) -> float | str:
    if not values:
        return ""

    return round(
        mean(values),
        2,
    )


def safe_median(
    values: list[int],
) -> float | str:
    if not values:
        return ""

    return round(
        median(values),
        1,
    )


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

    intensity_rows: list[
        dict[str, Any]
    ] = []

    activity_rows: list[
        dict[str, Any]
    ] = []

    for from_year, to_year in (
        (2023, 2024),
        (2024, 2025),
    ):
        origin_map = year_maps[
            from_year
        ]

        destination_keys = set(
            year_maps[to_year]
        )

        for population in (
            "ALL",
            "RELEVES",
            "JUNIOR",
            "U21",
            "OPEN",
            "SENIOR",
        ):
            selected = [
                row
                for row in origin_map.values()
                if (
                    population == "ALL"
                    or row["AgeBand"]
                    == population
                )
            ]

            retained_rows = [
                row
                for row in selected
                if row["AthleteKey"]
                in destination_keys
            ]

            exited_rows = [
                row
                for row in selected
                if row["AthleteKey"]
                not in destination_keys
            ]

            retained_activity = [
                as_int(
                    row["Competitions"]
                )
                for row in retained_rows
            ]

            exited_activity = [
                as_int(
                    row["Competitions"]
                )
                for row in exited_rows
            ]

            activity_rows.append(
                {
                    "FromYear": from_year,
                    "ToYear": to_year,
                    "Population": population,
                    "OriginAthletes": len(
                        selected
                    ),
                    "RetainedAthletes": len(
                        retained_rows
                    ),
                    "ExitedAthletes": len(
                        exited_rows
                    ),
                    "RetentionRatePercent": (
                        percent(
                            len(retained_rows),
                            len(selected),
                        )
                    ),
                    "MeanCompetitionsRetained": (
                        safe_mean(
                            retained_activity
                        )
                    ),
                    "MedianCompetitionsRetained": (
                        safe_median(
                            retained_activity
                        )
                    ),
                    "MeanCompetitionsExited": (
                        safe_mean(
                            exited_activity
                        )
                    ),
                    "MedianCompetitionsExited": (
                        safe_median(
                            exited_activity
                        )
                    ),
                }
            )

            band_groups: dict[
                str,
                list[dict[str, str]],
            ] = defaultdict(list)

            for row in selected:
                band_groups[
                    intensity_band(
                        as_int(
                            row["Competitions"]
                        )
                    )
                ].append(row)

            for band in sorted(
                band_groups,
                key=lambda value: (
                    INTENSITY_ORDER[
                        value
                    ]
                ),
            ):
                group = band_groups[
                    band
                ]

                retained = sum(
                    1
                    for row in group
                    if row["AthleteKey"]
                    in destination_keys
                )

                intensity_rows.append(
                    {
                        "FromYear": from_year,
                        "ToYear": to_year,
                        "Population": population,
                        "IntensityBand": band,
                        "OriginAthletes": len(
                            group
                        ),
                        "RetainedAthletes": (
                            retained
                        ),
                        "ExitedAthletes": (
                            len(group)
                            - retained
                        ),
                        "RetentionRatePercent": (
                            percent(
                                retained,
                                len(group),
                            )
                        ),
                    }
                )

    athletes_2023 = set(
        year_maps[2023]
    )

    athletes_2025 = set(
        year_maps[2025]
    )

    newcomer_groups: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for athlete_key, row in (
        year_maps[2024].items()
    ):
        status = (
            "NEW_IN_2024_WINDOW"
            if athlete_key
            not in athletes_2023
            else "ALREADY_PRESENT_2023"
        )

        newcomer_groups[
            status
        ].append(row)

    newcomer_rows: list[
        dict[str, Any]
    ] = []

    for status, group in sorted(
        newcomer_groups.items()
    ):
        retained = [
            row
            for row in group
            if row["AthleteKey"]
            in athletes_2025
        ]

        exited = [
            row
            for row in group
            if row["AthleteKey"]
            not in athletes_2025
        ]

        activities = [
            as_int(
                row["Competitions"]
            )
            for row in group
        ]

        retained_activities = [
            as_int(
                row["Competitions"]
            )
            for row in retained
        ]

        exited_activities = [
            as_int(
                row["Competitions"]
            )
            for row in exited
        ]

        newcomer_rows.append(
            {
                "Status2024": status,
                "Athletes2024": len(
                    group
                ),
                "Retained2025": len(
                    retained
                ),
                "Exited2025": len(
                    exited
                ),
                "RetentionRatePercent": (
                    percent(
                        len(retained),
                        len(group),
                    )
                ),
                "MeanCompetitions2024": (
                    safe_mean(
                        activities
                    )
                ),
                "MeanCompetitionsRetained": (
                    safe_mean(
                        retained_activities
                    )
                ),
                "MeanCompetitionsExited": (
                    safe_mean(
                        exited_activities
                    )
                ),
            }
        )

    write_csv(
        SUMMARY_OUTPUT,
        intensity_rows,
    )

    write_csv(
        ACTIVITY_OUTPUT,
        activity_rows,
    )

    write_csv(
        NEWCOMER_OUTPUT,
        newcomer_rows,
    )

    print("=" * 115)
    print(
        "RÉTENTION SELON LE NOMBRE DE "
        "COMPÉTITIONS DE LA SAISON D'ORIGINE"
    )
    print("=" * 115)

    overall_intensity = [
        row
        for row in intensity_rows
        if row["Population"] == "ALL"
    ]

    print(
        f"{'Transition':<14}"
        f"{'Intensité':<23}"
        f"{'Sportifs':>10}"
        f"{'Maintenus':>11}"
        f"{'Sortants':>10}"
        f"{'Rétention':>12}"
    )
    print("-" * 82)

    for row in overall_intensity:
        print(
            f"{row['FromYear']}→"
            f"{row['ToYear']:<8}"
            f"{row['IntensityBand']:<23}"
            f"{row['OriginAthletes']:>10}"
            f"{row['RetainedAthletes']:>11}"
            f"{row['ExitedAthletes']:>10}"
            f"{float(row['RetentionRatePercent']):>11.1f}%"
        )

    print()
    print("=" * 115)
    print(
        "ACTIVITÉ AVANT MAINTIEN OU SORTIE"
    )
    print("=" * 115)

    overall_activity = [
        row
        for row in activity_rows
        if row["Population"] == "ALL"
    ]

    print(
        f"{'Transition':<14}"
        f"{'Maintenus':>11}"
        f"{'Moy. maint.':>13}"
        f"{'Méd. maint.':>13}"
        f"{'Sortants':>11}"
        f"{'Moy. sort.':>12}"
        f"{'Méd. sort.':>12}"
    )
    print("-" * 89)

    for row in overall_activity:
        print(
            f"{row['FromYear']}→"
            f"{row['ToYear']:<8}"
            f"{row['RetainedAthletes']:>11}"
            f"{float(row['MeanCompetitionsRetained']):>13.2f}"
            f"{float(row['MedianCompetitionsRetained']):>13.1f}"
            f"{row['ExitedAthletes']:>11}"
            f"{float(row['MeanCompetitionsExited']):>12.2f}"
            f"{float(row['MedianCompetitionsExited']):>12.1f}"
        )

    print()
    print("=" * 115)
    print(
        "ENTRANTS 2024 ET COMPÉTITEURS "
        "DÉJÀ PRÉSENTS EN 2023"
    )
    print("=" * 115)

    print(
        f"{'Statut':<26}"
        f"{'Sportifs':>10}"
        f"{'Maintenus':>11}"
        f"{'Sortants':>10}"
        f"{'Rétention':>12}"
        f"{'Moy. compét.':>14}"
    )
    print("-" * 86)

    for row in newcomer_rows:
        print(
            f"{row['Status2024']:<26}"
            f"{row['Athletes2024']:>10}"
            f"{row['Retained2025']:>11}"
            f"{row['Exited2025']:>10}"
            f"{float(row['RetentionRatePercent']):>11.1f}%"
            f"{float(row['MeanCompetitions2024']):>14.2f}"
        )

    print()
    print("Intensité :", SUMMARY_OUTPUT)
    print("Maintien  :", ACTIVITY_OUTPUT)
    print("Entrants  :", NEWCOMER_OUTPUT)


if __name__ == "__main__":
    main()