"""Mesure la concentration de l'activité compétitive EMS sur 2023-2025."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    ROOT
    / "data/processed"
    / "ems_panel_competiteurs_francais_2023_2025.csv"
)

SUMMARY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_concentration_activite_2023_2025.csv"
)

LORENZ_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_courbe_lorenz_activite_2023_2025.csv"
)


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
    numerator: int | float,
    denominator: int | float,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        100 * numerator / denominator,
        1,
    )


def gini(values: list[int]) -> float:
    clean_values = sorted(
        max(0, value)
        for value in values
    )

    count = len(clean_values)
    total = sum(clean_values)

    if count == 0 or total == 0:
        return 0.0

    weighted_sum = sum(
        index * value
        for index, value in enumerate(
            clean_values,
            start=1,
        )
    )

    coefficient = (
        2 * weighted_sum
        / (count * total)
        - (count + 1) / count
    )

    return round(
        coefficient,
        4,
    )


def top_n_row(
    sorted_rows: list[dict[str, Any]],
    total_activity: int,
    top_n: int,
    label: str,
) -> dict[str, Any]:
    selected = sorted_rows[:top_n]

    activity = sum(
        row["TotalCompetitions"]
        for row in selected
    )

    return {
        "Indicator": label,
        "Athletes": len(selected),
        "AthleteSharePercent": percent(
            len(selected),
            len(sorted_rows),
        ),
        "CompetitionParticipations": activity,
        "ActivitySharePercent": percent(
            activity,
            total_activity,
        ),
        "MeanCompetitionsPerAthlete": round(
            activity / len(selected),
            2,
        ) if selected else 0,
    }


def main() -> None:
    raw_rows = read_csv(
        SOURCE_FILE
    )

    athletes = [
        {
            "AthleteKey": row["AthleteKey"],
            "Name": row["Name"],
            "FidelityProfile": (
                row["FidelityProfile"]
            ),
            "TotalCompetitions": as_int(
                row["TotalCompetitions"]
            ),
        }
        for row in raw_rows
    ]

    athletes_desc = sorted(
        athletes,
        key=lambda row: (
            -row["TotalCompetitions"],
            row["Name"],
        ),
    )

    activity_values = [
        row["TotalCompetitions"]
        for row in athletes
    ]

    total_athletes = len(
        athletes
    )

    total_activity = sum(
        activity_values
    )

    top_10_percent_n = max(
        1,
        round(
            total_athletes * 0.10
        ),
    )

    top_20_percent_n = max(
        1,
        round(
            total_athletes * 0.20
        ),
    )

    top_50_percent_n = max(
        1,
        round(
            total_athletes * 0.50
        ),
    )

    summary_rows = [
        top_n_row(
            athletes_desc,
            total_activity,
            10,
            "TOP_10_ATHLETES",
        ),
        top_n_row(
            athletes_desc,
            total_activity,
            20,
            "TOP_20_ATHLETES",
        ),
        top_n_row(
            athletes_desc,
            total_activity,
            50,
            "TOP_50_ATHLETES",
        ),
        top_n_row(
            athletes_desc,
            total_activity,
            top_10_percent_n,
            "TOP_10_PERCENT",
        ),
        top_n_row(
            athletes_desc,
            total_activity,
            top_20_percent_n,
            "TOP_20_PERCENT",
        ),
        top_n_row(
            athletes_desc,
            total_activity,
            top_50_percent_n,
            "TOP_50_PERCENT",
        ),
    ]

    athletes_ascending = sorted(
        athletes,
        key=lambda row: (
            row["TotalCompetitions"],
            row["Name"],
        ),
    )

    cumulative_activity = 0
    lorenz_rows: list[
        dict[str, Any]
    ] = [
        {
            "AthleteRankAscending": 0,
            "AthletePopulationPercent": 0.0,
            "CumulativeActivity": 0,
            "CumulativeActivityPercent": 0.0,
        }
    ]

    for index, row in enumerate(
        athletes_ascending,
        start=1,
    ):
        cumulative_activity += (
            row["TotalCompetitions"]
        )

        lorenz_rows.append(
            {
                "AthleteRankAscending": index,
                "AthletePopulationPercent": round(
                    100 * index
                    / total_athletes,
                    2,
                ),
                "CumulativeActivity": (
                    cumulative_activity
                ),
                "CumulativeActivityPercent": round(
                    100 * cumulative_activity
                    / total_activity,
                    2,
                ),
            }
        )

    write_csv(
        SUMMARY_OUTPUT,
        summary_rows,
    )

    write_csv(
        LORENZ_OUTPUT,
        lorenz_rows,
    )

    print("=" * 115)
    print(
        "CONCENTRATION DE L'ACTIVITÉ "
        "COMPÉTITIVE EMS — 2023 À 2025"
    )
    print("=" * 115)

    print(
        "Compétiteurs distincts :",
        total_athletes,
    )

    print(
        "Participations totales :",
        total_activity,
    )

    print(
        "Coefficient de Gini    :",
        gini(activity_values),
    )

    print()
    print(
        f"{'Indicateur':<22}"
        f"{'Sportifs':>10}"
        f"{'Part pop.':>12}"
        f"{'Particip.':>12}"
        f"{'Part activité':>15}"
        f"{'Moyenne':>11}"
    )
    print("-" * 84)

    for row in summary_rows:
        print(
            f"{row['Indicator']:<22}"
            f"{row['Athletes']:>10}"
            f"{float(row['AthleteSharePercent']):>11.1f}%"
            f"{row['CompetitionParticipations']:>12}"
            f"{float(row['ActivitySharePercent']):>14.1f}%"
            f"{float(row['MeanCompetitionsPerAthlete']):>11.2f}"
        )

    print()
    print("DÉCILES DE POPULATION")
    print("=" * 115)

    for threshold in (
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
    ):
        closest = min(
            lorenz_rows,
            key=lambda row: abs(
                float(
                    row[
                        "AthletePopulationPercent"
                    ]
                )
                - threshold
            ),
        )

        print(
            f"{threshold:>3}% des sportifs "
            f"les moins actifs réalisent "
            f"{float(closest['CumulativeActivityPercent']):>5.1f}% "
            f"de l'activité"
        )

    print()
    print("Synthèse :", SUMMARY_OUTPUT)
    print("Lorenz   :", LORENZ_OUTPUT)


if __name__ == "__main__":
    main()