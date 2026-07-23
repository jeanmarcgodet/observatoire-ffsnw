"""Analyse longitudinale de la fidélisation des compétiteurs français EMS."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

YEARS = (2023, 2024, 2025)

SOURCE_FILES = {
    year: (
        ROOT
        / "data/processed"
        / f"ems_participations_france_waterski_{year}.csv"
    )
    for year in YEARS
}

PANEL_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_panel_competiteurs_francais_2023_2025.csv"
)

TRANSITIONS_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_transitions_competiteurs_2023_2025.csv"
)

PROFILES_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_profils_fidelisation_2023_2025.csv"
)

COHORTS_OUTPUT = (
    ROOT
    / "data/processed"
    / "ems_cohortes_retention_2023_2025.csv"
)


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
    "competition_code": (
        "CompetitionCode",
        "CompetitionId",
        "IwwfId",
        "Code",
        "competition_code",
        "iwwf_id",
    ),
    "competition_name": (
        "CompetitionName",
        "Competition",
        "NomCompetition",
        "competition_name",
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
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if fieldnames is None:
        if not rows:
            return
        fieldnames = list(rows[0].keys())

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def find_column(
    columns: list[str],
    logical_name: str,
    required: bool = True,
) -> str | None:
    candidates = COLUMN_CANDIDATES[logical_name]

    for candidate in candidates:
        if candidate in columns:
            return candidate

    lower_lookup = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:
        if candidate.lower() in lower_lookup:
            return lower_lookup[candidate.lower()]

    if required:
        raise RuntimeError(
            f"Colonne introuvable pour {logical_name}. "
            f"Colonnes disponibles : {columns}"
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
        if not unicodedata.combining(character)
    )

    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def parse_athlete_key(
    value: str,
) -> tuple[str, str, str]:
    parts = str(value or "").split("|")

    if len(parts) >= 3:
        return (
            parts[0].strip().upper(),
            parts[1].strip(),
            "|".join(parts[2:]).strip(),
        )

    return "", "", ""


def canonical_athlete_key(
    row: dict[str, str],
    columns: dict[str, str | None],
) -> tuple[str, str, str, str]:
    raw_key = str(
        row.get(
            columns["athlete_key"] or "",
            "",
        )
    ).strip()

    key_country, key_yob, key_name = (
        parse_athlete_key(raw_key)
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

    display_name = str(
        row.get(
            columns["name"] or "",
            "",
        )
    ).strip() or key_name

    normalized_name = normalize_text(
        display_name or key_name
    )

    canonical_key = (
        f"{country}|{yob}|{normalized_name}"
    )

    return (
        canonical_key,
        country,
        yob,
        display_name,
    )


def classify_profile(
    active_years: tuple[int, ...],
) -> str:
    if active_years == (2023, 2024, 2025):
        return "CORE_3_YEARS"

    if active_years == (2023, 2024):
        return "TWO_YEARS_2023_2024"

    if active_years == (2024, 2025):
        return "TWO_YEARS_2024_2025"

    if active_years == (2023, 2025):
        return "RETURN_AFTER_GAP"

    if active_years == (2023,):
        return "ONE_SEASON_2023"

    if active_years == (2024,):
        return "ONE_SEASON_2024"

    if active_years == (2025,):
        return "ONE_SEASON_2025"

    return "OTHER"


def intensity_level(
    competition_counts: list[int],
) -> str:
    active_counts = [
        value
        for value in competition_counts
        if value > 0
    ]

    if not active_counts:
        return "NO_ACTIVITY"

    average = (
        sum(active_counts)
        / len(active_counts)
    )

    if average < 2:
        return "OCCASIONAL"

    if average < 4:
        return "REGULAR"

    return "HIGHLY_ACTIVE"


def safe_percent(
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
    athlete_data: dict[
        str,
        dict[str, Any],
    ] = {}

    annual_sets: dict[
        int,
        set[str],
    ] = {
        year: set()
        for year in YEARS
    }

    annual_appearances: dict[
        int,
        dict[str, set[str]],
    ] = {
        year: defaultdict(set)
        for year in YEARS
    }

    print("=" * 110)
    print("LECTURE DES FICHIERS EMS")
    print("=" * 110)

    for year, path in SOURCE_FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Fichier absent : {path}"
            )

        rows = read_csv(path)

        if not rows:
            raise RuntimeError(
                f"Fichier vide : {path}"
            )

        columns_list = list(
            rows[0].keys()
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
            "competition_code": find_column(
                columns_list,
                "competition_code",
            ),
            "competition_name": find_column(
                columns_list,
                "competition_name",
                required=False,
            ),
        }

        french_rows = 0

        for row in rows:
            (
                athlete_key,
                country,
                yob,
                display_name,
            ) = canonical_athlete_key(
                row,
                columns,
            )

            if country != "FRA":
                continue

            french_rows += 1

            competition_code = str(
                row.get(
                    columns[
                        "competition_code"
                    ] or "",
                    "",
                )
            ).strip()

            if not competition_code:
                continue

            annual_sets[year].add(
                athlete_key
            )

            annual_appearances[year][
                athlete_key
            ].add(
                competition_code
            )

            if athlete_key not in athlete_data:
                athlete_data[athlete_key] = {
                    "AthleteKey": athlete_key,
                    "Name": display_name,
                    "Country": country,
                    "YOB": yob,
                    "_names": set(),
                }

            athlete_data[athlete_key][
                "_names"
            ].add(
                display_name
            )

        print(
            f"{year} : "
            f"{len(rows)} lignes, "
            f"{french_rows} lignes françaises, "
            f"{len(annual_sets[year])} sportifs"
        )

    panel_rows: list[dict[str, Any]] = []

    for athlete_key in sorted(
        athlete_data
    ):
        item = athlete_data[
            athlete_key
        ]

        counts = {
            year: len(
                annual_appearances[year].get(
                    athlete_key,
                    set(),
                )
            )
            for year in YEARS
        }

        active_years = tuple(
            year
            for year in YEARS
            if counts[year] > 0
        )

        total_competitions = sum(
            counts.values()
        )

        panel_rows.append(
            {
                "AthleteKey": athlete_key,
                "Name": sorted(
                    item["_names"],
                    key=lambda value: (
                        -len(value),
                        value,
                    ),
                )[0],
                "Country": item["Country"],
                "YOB": item["YOB"],
                "Present2023": int(
                    counts[2023] > 0
                ),
                "Present2024": int(
                    counts[2024] > 0
                ),
                "Present2025": int(
                    counts[2025] > 0
                ),
                "Competitions2023": (
                    counts[2023]
                ),
                "Competitions2024": (
                    counts[2024]
                ),
                "Competitions2025": (
                    counts[2025]
                ),
                "ActiveSeasons": len(
                    active_years
                ),
                "ActiveYears": " | ".join(
                    str(year)
                    for year in active_years
                ),
                "TotalCompetitions": (
                    total_competitions
                ),
                "MeanCompetitionsPerActiveSeason": (
                    round(
                        total_competitions
                        / len(active_years),
                        2,
                    )
                    if active_years
                    else 0
                ),
                "FidelityProfile": (
                    classify_profile(
                        active_years
                    )
                ),
                "IntensityProfile": (
                    intensity_level(
                        list(counts.values())
                    )
                ),
            }
        )

    profile_counts = Counter(
        row["FidelityProfile"]
        for row in panel_rows
    )

    profile_rows = [
        {
            "FidelityProfile": profile,
            "Athletes": count,
            "ShareOfThreeYearPoolPercent": (
                safe_percent(
                    count,
                    len(panel_rows),
                )
            ),
        }
        for profile, count in sorted(
            profile_counts.items()
        )
    ]

    transition_rows: list[
        dict[str, Any]
    ] = []

    for previous_year, current_year in (
        (2023, 2024),
        (2024, 2025),
    ):
        previous = annual_sets[
            previous_year
        ]

        current = annual_sets[
            current_year
        ]

        retained = (
            previous
            & current
        )

        exits = (
            previous
            - current
        )

        entrants = (
            current
            - previous
        )

        transition_rows.append(
            {
                "FromYear": previous_year,
                "ToYear": current_year,
                "PreviousAthletes": len(
                    previous
                ),
                "CurrentAthletes": len(
                    current
                ),
                "RetainedAthletes": len(
                    retained
                ),
                "ExitedAthletes": len(
                    exits
                ),
                "EntrantAthletes": len(
                    entrants
                ),
                "RetentionRatePercent": (
                    safe_percent(
                        len(retained),
                        len(previous),
                    )
                ),
                "ExitRatePercent": (
                    safe_percent(
                        len(exits),
                        len(previous),
                    )
                ),
                "EntrantShareOfCurrentPercent": (
                    safe_percent(
                        len(entrants),
                        len(current),
                    )
                ),
                "NetChangeAthletes": (
                    len(current)
                    - len(previous)
                ),
            }
        )

    cohort_2023 = annual_sets[2023]
    cohort_2024 = annual_sets[2024]

    cohort_rows = [
        {
            "Cohort": "ACTIVE_2023",
            "InitialAthletes": len(
                cohort_2023
            ),
            "RetainedNextYear": len(
                cohort_2023
                & annual_sets[2024]
            ),
            "RetainedNextYearPercent": (
                safe_percent(
                    len(
                        cohort_2023
                        & annual_sets[2024]
                    ),
                    len(cohort_2023),
                )
            ),
            "PresentIn2025": len(
                cohort_2023
                & annual_sets[2025]
            ),
            "PresentIn2025Percent": (
                safe_percent(
                    len(
                        cohort_2023
                        & annual_sets[2025]
                    ),
                    len(cohort_2023),
                )
            ),
            "PresentAllThreeYears": len(
                cohort_2023
                & annual_sets[2024]
                & annual_sets[2025]
            ),
            "PresentAllThreeYearsPercent": (
                safe_percent(
                    len(
                        cohort_2023
                        & annual_sets[2024]
                        & annual_sets[2025]
                    ),
                    len(cohort_2023),
                )
            ),
            "ReturnAfterGap": len(
                (
                    cohort_2023
                    - annual_sets[2024]
                )
                & annual_sets[2025]
            ),
        },
        {
            "Cohort": "ACTIVE_2024",
            "InitialAthletes": len(
                cohort_2024
            ),
            "RetainedNextYear": len(
                cohort_2024
                & annual_sets[2025]
            ),
            "RetainedNextYearPercent": (
                safe_percent(
                    len(
                        cohort_2024
                        & annual_sets[2025]
                    ),
                    len(cohort_2024),
                )
            ),
            "PresentIn2025": len(
                cohort_2024
                & annual_sets[2025]
            ),
            "PresentIn2025Percent": (
                safe_percent(
                    len(
                        cohort_2024
                        & annual_sets[2025]
                    ),
                    len(cohort_2024),
                )
            ),
            "PresentAllThreeYears": "",
            "PresentAllThreeYearsPercent": "",
            "ReturnAfterGap": "",
        },
    ]

    write_csv(
        PANEL_OUTPUT,
        panel_rows,
    )

    write_csv(
        TRANSITIONS_OUTPUT,
        transition_rows,
    )

    write_csv(
        PROFILES_OUTPUT,
        profile_rows,
    )

    write_csv(
        COHORTS_OUTPUT,
        cohort_rows,
    )

    print()
    print("=" * 110)
    print("PROFILS DE FIDÉLISATION")
    print("=" * 110)

    print(
        f"{'Profil':<30}"
        f"{'Sportifs':>10}"
        f"{'Part':>12}"
    )
    print("-" * 52)

    profile_order = (
        "CORE_3_YEARS",
        "TWO_YEARS_2023_2024",
        "TWO_YEARS_2024_2025",
        "RETURN_AFTER_GAP",
        "ONE_SEASON_2023",
        "ONE_SEASON_2024",
        "ONE_SEASON_2025",
        "OTHER",
    )

    for profile in profile_order:
        count = profile_counts.get(
            profile,
            0,
        )

        if count == 0:
            continue

        print(
            f"{profile:<30}"
            f"{count:>10}"
            f"{safe_percent(count, len(panel_rows)):>11}%"
        )

    print()
    print("=" * 110)
    print("TRANSITIONS ANNUELLES")
    print("=" * 110)

    print(
        f"{'Transition':<14}"
        f"{'Départ':>9}"
        f"{'Arrivée':>10}"
        f"{'Fidèles':>10}"
        f"{'Sortants':>10}"
        f"{'Entrants':>10}"
        f"{'Rétention':>12}"
    )
    print("-" * 77)

    for row in transition_rows:
        print(
            f"{row['FromYear']}→{row['ToYear']:<8}"
            f"{row['PreviousAthletes']:>9}"
            f"{row['CurrentAthletes']:>10}"
            f"{row['RetainedAthletes']:>10}"
            f"{row['ExitedAthletes']:>10}"
            f"{row['EntrantAthletes']:>10}"
            f"{float(row['RetentionRatePercent']):>11.1f}%"
        )

    print()
    print("=" * 110)
    print("COHORTE 2023")
    print("=" * 110)

    core = (
        annual_sets[2023]
        & annual_sets[2024]
        & annual_sets[2025]
    )

    return_after_gap = (
        annual_sets[2023]
        - annual_sets[2024]
    ) & annual_sets[2025]

    print(
        "Sportifs actifs en 2023             :",
        len(annual_sets[2023]),
    )
    print(
        "Encore actifs en 2024               :",
        len(
            annual_sets[2023]
            & annual_sets[2024]
        ),
    )
    print(
        "Encore présents en 2025             :",
        len(
            annual_sets[2023]
            & annual_sets[2025]
        ),
    )
    print(
        "Présents pendant les trois saisons  :",
        len(core),
    )
    print(
        "Retour en 2025 après absence en 2024:",
        len(return_after_gap),
    )

    competition_totals = [
        int(row["TotalCompetitions"])
        for row in panel_rows
    ]

    print()
    print("=" * 110)
    print("INTENSITÉ SUR TROIS SAISONS")
    print("=" * 110)

    print(
        "Compétiteurs distincts 2023–2025 :",
        len(panel_rows),
    )
    print(
        "Nombre médian de compétitions     :",
        median(competition_totals)
        if competition_totals
        else 0,
    )
    print(
        "Compétiteurs présents une saison  :",
        sum(
            1
            for row in panel_rows
            if int(row["ActiveSeasons"]) == 1
        ),
    )
    print(
        "Compétiteurs présents deux saisons:",
        sum(
            1
            for row in panel_rows
            if int(row["ActiveSeasons"]) == 2
        ),
    )
    print(
        "Compétiteurs présents trois saisons:",
        sum(
            1
            for row in panel_rows
            if int(row["ActiveSeasons"]) == 3
        ),
    )

    print()
    print("Panel       :", PANEL_OUTPUT)
    print("Transitions :", TRANSITIONS_OUTPUT)
    print("Profils     :", PROFILES_OUTPUT)
    print("Cohortes    :", COHORTS_OUTPUT)


if __name__ == "__main__":
    main()