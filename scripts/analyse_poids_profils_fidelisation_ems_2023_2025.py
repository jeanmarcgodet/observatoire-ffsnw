"""Mesure le poids des profils de fidélisation dans l'activité EMS."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PANEL_FILE = (
    ROOT
    / "data/processed"
    / "ems_panel_competiteurs_francais_2023_2025.csv"
)

PROFILE_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_poids_profils_fidelisation_2023_2025.csv"
)

ANNUAL_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_poids_profils_par_annee_2023_2025.csv"
)

INTENSITY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_fidelisation_par_intensite_2023_2025.csv"
)


PROFILE_ORDER = (
    "CORE_3_YEARS",
    "TWO_YEARS_2023_2024",
    "TWO_YEARS_2024_2025",
    "RETURN_AFTER_GAP",
    "ONE_SEASON_2023",
    "ONE_SEASON_2024",
    "ONE_SEASON_2025",
    "OTHER",
)

INTENSITY_ORDER = (
    "OCCASIONAL",
    "REGULAR",
    "HIGHLY_ACTIVE",
    "NO_ACTIVITY",
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


def as_float(value: Any) -> float:
    try:
        return float(
            str(value or "0").replace(",", ".")
        )
    except (TypeError, ValueError):
        return 0.0


def percent(
    numerator: int | float,
    denominator: int | float,
) -> float | str:
    if denominator == 0:
        return ""

    return round(
        100 * numerator / denominator,
        1,
    )


def main() -> None:
    rows = read_csv(PANEL_FILE)

    if not rows:
        raise RuntimeError(
            f"Panel vide : {PANEL_FILE}"
        )

    total_athletes = len(rows)

    total_competitions = sum(
        as_int(row["TotalCompetitions"])
        for row in rows
    )

    profile_groups: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        profile_groups[
            row["FidelityProfile"]
        ].append(row)

    profile_rows: list[dict[str, Any]] = []

    for profile in PROFILE_ORDER:
        group = profile_groups.get(
            profile,
            [],
        )

        if not group:
            continue

        competition_counts = [
            as_int(row["TotalCompetitions"])
            for row in group
        ]

        active_seasons = [
            as_int(row["ActiveSeasons"])
            for row in group
        ]

        group_competitions = sum(
            competition_counts
        )

        group_active_seasons = sum(
            active_seasons
        )

        profile_rows.append(
            {
                "FidelityProfile": profile,
                "Athletes": len(group),
                "AthleteSharePercent": percent(
                    len(group),
                    total_athletes,
                ),
                "CompetitionParticipations": (
                    group_competitions
                ),
                "CompetitionSharePercent": percent(
                    group_competitions,
                    total_competitions,
                ),
                "MeanCompetitionsPerAthlete": round(
                    group_competitions
                    / len(group),
                    2,
                ),
                "MedianCompetitionsPerAthlete": (
                    median(
                        competition_counts
                    )
                ),
                "MeanCompetitionsPerActiveSeason": (
                    round(
                        group_competitions
                        / group_active_seasons,
                        2,
                    )
                    if group_active_seasons
                    else 0
                ),
                "AthletesWithOneCompetitionTotal": sum(
                    1
                    for value in competition_counts
                    if value == 1
                ),
                "AthletesWithFiveOrMoreCompetitions": (
                    sum(
                        1
                        for value in competition_counts
                        if value >= 5
                    )
                ),
                "AthletesWithTenOrMoreCompetitions": (
                    sum(
                        1
                        for value in competition_counts
                        if value >= 10
                    )
                ),
            }
        )

    annual_rows: list[dict[str, Any]] = []

    for year in (2023, 2024, 2025):
        column = f"Competitions{year}"

        annual_total_athletes = sum(
            1
            for row in rows
            if as_int(row[column]) > 0
        )

        annual_total_competitions = sum(
            as_int(row[column])
            for row in rows
        )

        for profile in PROFILE_ORDER:
            group = [
                row
                for row in profile_groups.get(
                    profile,
                    [],
                )
                if as_int(row[column]) > 0
            ]

            if not group:
                continue

            competitions = sum(
                as_int(row[column])
                for row in group
            )

            annual_rows.append(
                {
                    "Year": year,
                    "FidelityProfile": profile,
                    "ActiveAthletes": len(group),
                    "ShareOfAnnualAthletesPercent": (
                        percent(
                            len(group),
                            annual_total_athletes,
                        )
                    ),
                    "CompetitionParticipations": (
                        competitions
                    ),
                    "ShareOfAnnualCompetitionsPercent": (
                        percent(
                            competitions,
                            annual_total_competitions,
                        )
                    ),
                    "MeanCompetitionsPerActiveAthlete": (
                        round(
                            competitions
                            / len(group),
                            2,
                        )
                    ),
                }
            )

    intensity_counts: dict[
        tuple[str, str],
        int,
    ] = Counter(
        (
            row["FidelityProfile"],
            row["IntensityProfile"],
        )
        for row in rows
    )

    intensity_rows: list[dict[str, Any]] = []

    for profile in PROFILE_ORDER:
        profile_total = len(
            profile_groups.get(
                profile,
                [],
            )
        )

        if profile_total == 0:
            continue

        for intensity in INTENSITY_ORDER:
            count = intensity_counts.get(
                (
                    profile,
                    intensity,
                ),
                0,
            )

            if count == 0:
                continue

            intensity_rows.append(
                {
                    "FidelityProfile": profile,
                    "IntensityProfile": intensity,
                    "Athletes": count,
                    "ShareWithinFidelityProfilePercent": (
                        percent(
                            count,
                            profile_total,
                        )
                    ),
                    "ShareOfTotalPoolPercent": (
                        percent(
                            count,
                            total_athletes,
                        )
                    ),
                }
            )

    write_csv(
        PROFILE_OUTPUT,
        profile_rows,
    )

    write_csv(
        ANNUAL_OUTPUT,
        annual_rows,
    )

    write_csv(
        INTENSITY_OUTPUT,
        intensity_rows,
    )

    print("=" * 125)
    print(
        "POIDS DES PROFILS DE FIDÉLISATION "
        "DANS L'ACTIVITÉ EMS"
    )
    print("=" * 125)

    print(
        f"{'Profil':<29}"
        f"{'Sportifs':>10}"
        f"{'Part pop.':>11}"
        f"{'Compét.':>10}"
        f"{'Part act.':>11}"
        f"{'Moyenne':>10}"
        f"{'Médiane':>10}"
        f"{'Par saison':>12}"
    )
    print("-" * 105)

    for row in profile_rows:
        print(
            f"{row['FidelityProfile']:<29}"
            f"{row['Athletes']:>10}"
            f"{float(row['AthleteSharePercent']):>10.1f}%"
            f"{row['CompetitionParticipations']:>10}"
            f"{float(row['CompetitionSharePercent']):>10.1f}%"
            f"{float(row['MeanCompetitionsPerAthlete']):>10.2f}"
            f"{float(row['MedianCompetitionsPerAthlete']):>10.1f}"
            f"{float(row['MeanCompetitionsPerActiveSeason']):>12.2f}"
        )

    print()
    print("=" * 125)
    print("POIDS ANNUEL DU NOYAU PRÉSENT TROIS SAISONS")
    print("=" * 125)

    core_rows = [
        row
        for row in annual_rows
        if row["FidelityProfile"]
        == "CORE_3_YEARS"
    ]

    print(
        f"{'Année':<8}"
        f"{'Sportifs noyau':>16}"
        f"{'Part sportifs':>16}"
        f"{'Participations':>16}"
        f"{'Part activité':>15}"
        f"{'Moyenne':>11}"
    )
    print("-" * 84)

    for row in core_rows:
        print(
            f"{row['Year']:<8}"
            f"{row['ActiveAthletes']:>16}"
            f"{float(row['ShareOfAnnualAthletesPercent']):>15.1f}%"
            f"{row['CompetitionParticipations']:>16}"
            f"{float(row['ShareOfAnnualCompetitionsPercent']):>14.1f}%"
            f"{float(row['MeanCompetitionsPerActiveAthlete']):>11.2f}"
        )

    print()
    print("=" * 125)
    print("INTENSITÉ PAR PROFIL")
    print("=" * 125)

    print(
        f"{'Profil':<29}"
        f"{'Intensité':<18}"
        f"{'Sportifs':>10}"
        f"{'Part profil':>13}"
    )
    print("-" * 72)

    for row in intensity_rows:
        print(
            f"{row['FidelityProfile']:<29}"
            f"{row['IntensityProfile']:<18}"
            f"{row['Athletes']:>10}"
            f"{float(row['ShareWithinFidelityProfilePercent']):>12.1f}%"
        )

    print()
    print("Total sportifs              :", total_athletes)
    print("Participations-compétitions :", total_competitions)
    print()
    print("Profils :", PROFILE_OUTPUT)
    print("Annuel  :", ANNUAL_OUTPUT)
    print("Intensité :", INTENSITY_OUTPUT)


if __name__ == "__main__":
    main()