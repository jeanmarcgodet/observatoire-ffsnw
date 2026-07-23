"""Analyse la fidélisation 2025 selon les disciplines pratiquées en 2024."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_2024 = (
    ROOT
    / "data/processed"
    / "ems_participations_france_waterski_2024.csv"
)

ATHLETE_YEAR_FILE = (
    ROOT
    / "data/processed"
    / "ems_competiteurs_annee_sexe_age_2023_2025.csv"
)

SUMMARY_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_fidelisation_multidisciplinarite_2024_2025.csv"
)

DETAIL_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_competiteurs_2024_disciplines_retention_2025.csv"
)


PHYSICAL_EVENTS = {
    "Slalom": "SLALOM",
    "Tricks": "FIGURES",
    "Jump": "SAUT",
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
) -> str:
    key_country, key_yob, key_name = parse_key(
        row.get("AthleteKey", "")
    )

    country = str(
        row.get("Country", "")
    ).strip().upper() or key_country

    yob = str(
        row.get("YOB", "")
    ).strip() or key_yob

    name = str(
        row.get("Name", "")
    ).strip() or key_name

    return (
        f"{country}|{yob}|"
        f"{normalize_text(name)}"
    )


def is_registered(value: Any) -> bool:
    text = str(value or "").strip()

    return text not in {
        "",
        "-",
        "0",
        "NONE",
        "None",
    }


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


def discipline_profile(
    disciplines: set[str],
) -> str:
    if not disciplines:
        return "NO_PHYSICAL_DISCIPLINE"

    if disciplines == {"SLALOM"}:
        return "SLALOM_ONLY"

    if disciplines == {"FIGURES"}:
        return "FIGURES_ONLY"

    if disciplines == {"SAUT"}:
        return "SAUT_ONLY"

    return "+".join(
        event
        for event in (
            "SLALOM",
            "FIGURES",
            "SAUT",
        )
        if event in disciplines
    )


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


def main() -> None:
    participation_rows = read_csv(
        SOURCE_2024
    )

    athlete_year_rows = read_csv(
        ATHLETE_YEAR_FILE
    )

    year_maps: dict[
        int,
        dict[str, dict[str, str]],
    ] = {
        2023: {},
        2024: {},
        2025: {},
    }

    for row in athlete_year_rows:
        year = int(row["Year"])

        year_maps[year][
            row["AthleteKey"]
        ] = row

    athletes_2023 = set(
        year_maps[2023]
    )

    athletes_2025 = set(
        year_maps[2025]
    )

    aggregates: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in participation_rows:
        if str(
            row.get("Country", "")
        ).strip().upper() != "FRA":
            continue

        athlete_key = canonical_key(row)

        if athlete_key not in aggregates:
            reference = year_maps[2024].get(
                athlete_key,
                {},
            )

            aggregates[athlete_key] = {
                "AthleteKey": athlete_key,
                "Name": str(
                    row.get("Name", "")
                ).strip(),
                "Sex": reference.get(
                    "Sex",
                    "",
                ),
                "AgeBand": reference.get(
                    "AgeBand",
                    "",
                ),
                "_competitions": set(),
                "_disciplines": set(),
                "_discipline_entries": 0,
            }

        item = aggregates[
            athlete_key
        ]

        competition_code = str(
            row.get(
                "CompetitionCode",
                "",
            )
        ).strip()

        if competition_code:
            item["_competitions"].add(
                competition_code
            )

        for column, event in (
            PHYSICAL_EVENTS.items()
        ):
            if is_registered(
                row.get(column, "")
            ):
                item["_disciplines"].add(
                    event
                )

                item[
                    "_discipline_entries"
                ] += 1

    detail_rows: list[
        dict[str, Any]
    ] = []

    for athlete_key, item in (
        aggregates.items()
    ):
        disciplines = item[
            "_disciplines"
        ]

        competitions = len(
            item["_competitions"]
        )

        detail_rows.append(
            {
                "AthleteKey": athlete_key,
                "Name": item["Name"],
                "Sex": item["Sex"],
                "AgeBand": item[
                    "AgeBand"
                ],
                "CohortStatus2024": (
                    "ALREADY_PRESENT_2023"
                    if athlete_key
                    in athletes_2023
                    else "NEW_IN_2024_WINDOW"
                ),
                "Competitions2024": (
                    competitions
                ),
                "IntensityBand": (
                    intensity_band(
                        competitions
                    )
                ),
                "PhysicalDisciplineCount": (
                    len(disciplines)
                ),
                "DisciplineProfile": (
                    discipline_profile(
                        disciplines
                    )
                ),
                "PhysicalDisciplineEntries": (
                    item[
                        "_discipline_entries"
                    ]
                ),
                "Present2025": int(
                    athlete_key
                    in athletes_2025
                ),
            }
        )

    dimensions = (
        "COHORT",
        "DISCIPLINE_COUNT",
        "DISCIPLINE_PROFILE",
        "COHORT_X_DISCIPLINE_COUNT",
        "COHORT_X_INTENSITY_X_DISCIPLINE_COUNT",
    )

    summary_rows: list[
        dict[str, Any]
    ] = []

    def group_value(
        row: dict[str, Any],
        dimension: str,
    ) -> str:
        if dimension == "COHORT":
            return str(
                row["CohortStatus2024"]
            )

        if dimension == "DISCIPLINE_COUNT":
            return str(
                row[
                    "PhysicalDisciplineCount"
                ]
            )

        if dimension == "DISCIPLINE_PROFILE":
            return str(
                row["DisciplineProfile"]
            )

        if dimension == (
            "COHORT_X_DISCIPLINE_COUNT"
        ):
            return (
                f"{row['CohortStatus2024']}|"
                f"{row['PhysicalDisciplineCount']}"
            )

        if dimension == (
            "COHORT_X_INTENSITY_X_DISCIPLINE_COUNT"
        ):
            return (
                f"{row['CohortStatus2024']}|"
                f"{row['IntensityBand']}|"
                f"{row['PhysicalDisciplineCount']}"
            )

        raise ValueError(dimension)

    for dimension in dimensions:
        groups: dict[
            str,
            list[dict[str, Any]],
        ] = defaultdict(list)

        for row in detail_rows:
            groups[
                group_value(
                    row,
                    dimension,
                )
            ].append(row)

        for group in sorted(groups):
            selected = groups[group]

            retained = sum(
                int(row["Present2025"])
                for row in selected
            )

            summary_rows.append(
                {
                    "Dimension": dimension,
                    "Group": group,
                    "Athletes2024": len(
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
                    "MeanDisciplineCount": (
                        round(
                            sum(
                                int(
                                    row[
                                        "PhysicalDisciplineCount"
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

    detail_rows.sort(
        key=lambda row: (
            str(
                row[
                    "CohortStatus2024"
                ]
            ),
            -int(
                row[
                    "PhysicalDisciplineCount"
                ]
            ),
            -int(
                row[
                    "Competitions2024"
                ]
            ),
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

    print("=" * 115)
    print(
        "FIDÉLISATION SELON LA "
        "MULTIDISCIPLINARITÉ EN 2024"
    )
    print("=" * 115)

    for cohort in (
        "NEW_IN_2024_WINDOW",
        "ALREADY_PRESENT_2023",
    ):
        print()
        print(cohort)
        print("-" * 90)

        selected_rows = [
            row
            for row in summary_rows
            if row["Dimension"]
            == "COHORT_X_DISCIPLINE_COUNT"
            and str(row["Group"]).startswith(
                cohort + "|"
            )
        ]

        print(
            f"{'Disciplines':<14}"
            f"{'Sportifs':>10}"
            f"{'Maintenus':>11}"
            f"{'Sortants':>10}"
            f"{'Rétention':>12}"
            f"{'Moy. compét.':>14}"
        )
        print("-" * 75)

        for row in selected_rows:
            discipline_count = str(
                row["Group"]
            ).split("|")[-1]

            print(
                f"{discipline_count:<14}"
                f"{row['Athletes2024']:>10}"
                f"{row['Present2025']:>11}"
                f"{row['Absent2025']:>10}"
                f"{float(row['RetentionRatePercent']):>11.1f}%"
                f"{float(row['MeanCompetitions2024']):>14.2f}"
            )

    print()
    print("PROFILS DISCIPLINAIRES — ENTRANTS 2024")
    print("-" * 100)

    entrants = [
        row
        for row in detail_rows
        if row["CohortStatus2024"]
        == "NEW_IN_2024_WINDOW"
    ]

    profile_groups: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in entrants:
        profile_groups[
            row["DisciplineProfile"]
        ].append(row)

    print(
        f"{'Profil':<30}"
        f"{'Sportifs':>10}"
        f"{'Maintenus':>11}"
        f"{'Rétention':>12}"
        f"{'Moy. compét.':>14}"
    )
    print("-" * 80)

    for profile in sorted(
        profile_groups
    ):
        selected = profile_groups[
            profile
        ]

        retained = sum(
            int(row["Present2025"])
            for row in selected
        )

        mean_competitions = (
            sum(
                int(
                    row[
                        "Competitions2024"
                    ]
                )
                for row in selected
            )
            / len(selected)
        )

        print(
            f"{profile:<30}"
            f"{len(selected):>10}"
            f"{retained:>11}"
            f"{percent(
                retained,
                len(selected),
            ):>11.1f}%"
            f"{mean_competitions:>14.2f}"
        )

    print()
    print("Synthèse :", SUMMARY_OUTPUT)
    print("Détail   :", DETAIL_OUTPUT)


if __name__ == "__main__":
    main()