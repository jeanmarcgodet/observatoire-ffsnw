"""Analyse les champs des Championnats de France à partir des inscriptions EMS."""

from __future__ import annotations

import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

YEARS = range(2023, 2027)

CHAMPIONSHIPS = [
    (2023, "23FRA017", "RELEVES"),
    (2023, "23FRA018", "U21_OPEN"),
    (2023, "23FRA023", "SENIOR"),
    (2024, "24FRA026", "RELEVES"),
    (2024, "24FRA027", "U21_OPEN"),
    (2024, "24FRA034", "SENIOR"),
    (2025, "25FRA016", "RELEVES"),
    (2025, "25FRA206", "U21_OPEN"),
    (2025, "25FRA018", "SENIOR"),
    (2026, "26FRA020", "RELEVES"),
    (2026, "26FRA021", "U21_OPEN"),
    (2026, "26FRA041", "SENIOR"),
]

EVENT_COLUMNS = [
    ("SLALOM", "Slalom"),
    ("FIGURES", "Tricks"),
    ("SAUT", "Jump"),
    ("COMBINE", "Overall"),
]

CATEGORY_PATTERN = re.compile(
    r"^(?P<base>-\d+|\d+\+|Open|Pro)"
    r"\s+(?P<sex>[FM])"
    r"\s+\((?P<age>\d+)\)"
    r"(?:\s+Div\s+(?P<division>\d+))?$",
    flags=re.IGNORECASE,
)

CATEGORY_ORDER = {
    "U8": 8,
    "U10": 10,
    "U12": 12,
    "U14": 14,
    "U17": 17,
    "U21": 21,
    "OPEN": 30,
    "PRO": 31,
    "35+": 35,
    "45+": 45,
    "55+": 55,
    "65+": 65,
    "70+": 70,
    "75+": 75,
    "80+": 80,
    "85+": 85,
}

ALLOWED_POPULATIONS = {
    "RELEVES": {"RELEVES", "JUNIOR"},
    "U21_OPEN": {"U21", "OPEN"},
    "SENIOR": {"SENIOR"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file, delimiter=";"))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

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

        if rows:
            writer.writerows(rows)


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def is_selected(value: str) -> bool:
    value = normalize_spaces(value)

    return bool(value and value != "-")


def parse_category(raw_category: str) -> dict[str, Any] | None:
    raw_category = normalize_spaces(raw_category)
    match = CATEGORY_PATTERN.fullmatch(raw_category)

    if match is None:
        return None

    base = match.group("base")
    sex = match.group("sex").upper()
    age = int(match.group("age"))
    division = match.group("division") or ""

    if base.startswith("-"):
        category = f"U{base[1:]}"
    elif base.lower() == "open":
        category = "OPEN"
    elif base.lower() == "pro":
        category = "PRO"
    else:
        category = base.upper()

    if category in {"U8", "U10", "U12", "U14"}:
        population = "RELEVES"
    elif category == "U17":
        population = "JUNIOR"
    elif category == "U21":
        population = "U21"
    elif category in {"OPEN", "PRO"}:
        population = "OPEN"
    elif category.endswith("+"):
        population = "SENIOR"
    else:
        population = "AUTRE"

    return {
        "CategoryRaw": raw_category,
        "Category": category,
        "CategoryOrder": CATEGORY_ORDER.get(category, 999),
        "PopulationGroup": population,
        "Sex": sex,
        "Age": age,
        "Division": division,
    }


def field_depth_class(field_size: int) -> str:
    if field_size <= 0:
        return "0"
    if field_size == 1:
        return "1"
    if field_size == 2:
        return "2"
    if field_size == 3:
        return "3"
    if field_size <= 5:
        return "4-5"
    if field_size <= 9:
        return "6-9"
    return "10+"


def main() -> None:
    all_rows: list[dict[str, str]] = []

    for year in YEARS:
        path = ROOT / (
            f"data/processed/"
            f"ems_participations_france_waterski_{year}.csv"
        )

        all_rows.extend(read_csv(path))

    championship_lookup = {
        code: {
            "Year": year,
            "ChampionshipBlock": block,
        }
        for year, code, block in CHAMPIONSHIPS
    }

    rows_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in all_rows:
        code = normalize_spaces(row.get("CompetitionCode", ""))

        if code in championship_lookup:
            rows_by_code[code].append(row)

    missing_codes = [
        code
        for _, code, _ in CHAMPIONSHIPS
        if code not in rows_by_code
    ]

    if missing_codes:
        raise RuntimeError(
            "Championnats introuvables : "
            + ", ".join(missing_codes)
        )

    participants: list[dict[str, Any]] = []
    field_entries: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []

    for year, code, championship_block in CHAMPIONSHIPS:
        competition_rows = rows_by_code[code]

        for row in competition_rows:
            parsed = parse_category(row.get("Category", ""))

            base_anomaly = {
                "Year": year,
                "CompetitionCode": code,
                "ChampionshipBlock": championship_block,
                "CompetitionName": row.get(
                    "CompetitionName",
                    "",
                ),
                "AthleteKey": row.get("AthleteKey", ""),
                "Name": row.get("Name", ""),
                "Country": row.get("Country", ""),
                "CategoryRaw": row.get("Category", ""),
            }

            if parsed is None:
                anomalies.append(
                    {
                        **base_anomaly,
                        "AnomalyType": "CATEGORY_UNPARSED",
                        "Detail": "Catégorie EMS non reconnue",
                    }
                )
                continue

            population = parsed["PopulationGroup"]

            title_eligible = (
                population
                in ALLOWED_POPULATIONS[championship_block]
            )

            if not title_eligible:
                anomalies.append(
                    {
                        **base_anomaly,
                        "AnomalyType": "BLOCK_CATEGORY_MISMATCH",
                        "Detail": (
                            f"{population} dans le bloc "
                            f"{championship_block}"
                        ),
                    }
                )

            participant = {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionName": row.get(
                    "CompetitionName",
                    "",
                ),
                "ChampionshipBlock": championship_block,
                "TitleEligible": int(title_eligible),
                "AthleteKey": row.get("AthleteKey", ""),
                "Name": row.get("Name", ""),
                "Country": row.get("Country", ""),
                "IsFrench": row.get("IsFrench", ""),
                "YOB": row.get("YOB", ""),
                **parsed,
                "SlalomSelected": int(
                    is_selected(row.get("Slalom", ""))
                ),
                "TricksSelected": int(
                    is_selected(row.get("Tricks", ""))
                ),
                "JumpSelected": int(
                    is_selected(row.get("Jump", ""))
                ),
                "OverallSelected": int(
                    is_selected(row.get("Overall", ""))
                ),
            }

            participants.append(participant)

            selected_events = 0

            for event, column in EVENT_COLUMNS:
                if not is_selected(row.get(column, "")):
                    continue

                selected_events += 1

                field_entries.append(
                    {
                        "Year": year,
                        "CompetitionCode": code,
                        "CompetitionName": row.get(
                            "CompetitionName",
                            "",
                        ),
                        "ChampionshipBlock": championship_block,
                        "TitleEligible": int(title_eligible),
                        "PopulationGroup": population,
                        "Category": parsed["Category"],
                        "CategoryOrder": parsed["CategoryOrder"],
                        "Sex": parsed["Sex"],
                        "Age": parsed["Age"],
                        "Division": parsed["Division"],
                        "Event": event,
                        "AthleteKey": row.get("AthleteKey", ""),
                        "Name": row.get("Name", ""),
                        "Country": row.get("Country", ""),
                        "IsFrench": row.get("IsFrench", ""),
                        "CategoryRaw": parsed["CategoryRaw"],
                    }
                )

            if selected_events == 0:
                anomalies.append(
                    {
                        **base_anomaly,
                        "AnomalyType": "NO_EVENT_SELECTED",
                        "Detail": (
                            "Participant sans épreuve sélectionnée"
                        ),
                    }
                )

    # ------------------------------------------------------------
    # Déduplication des participations à un champ
    # ------------------------------------------------------------

    deduplicated_entries: dict[
        tuple[Any, ...],
        dict[str, Any],
    ] = {}

    for entry in field_entries:
        key = (
            entry["Year"],
            entry["CompetitionCode"],
            entry["Category"],
            entry["Sex"],
            entry["Event"],
            entry["AthleteKey"],
        )

        deduplicated_entries[key] = entry

    field_entries = list(deduplicated_entries.values())

    title_field_entries = [
        entry
        for entry in field_entries
        if int(entry["TitleEligible"]) == 1
    ]

    parallel_field_entries = [
        entry
        for entry in field_entries
        if int(entry["TitleEligible"]) == 0
    ]

    # ------------------------------------------------------------
    # Synthèse par champ observé
    # ------------------------------------------------------------

    field_groups: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for entry in title_field_entries:
        key = (
            entry["Year"],
            entry["CompetitionCode"],
            entry["ChampionshipBlock"],
            entry["PopulationGroup"],
            entry["Category"],
            entry["CategoryOrder"],
            entry["Sex"],
            entry["Event"],
        )

        field_groups[key].append(entry)

    field_summary: list[dict[str, Any]] = []

    for key, entries in field_groups.items():
        (
            year,
            code,
            block,
            population,
            category,
            category_order,
            sex,
            event,
        ) = key

        all_athletes = {
            entry["AthleteKey"]
            for entry in entries
        }

        french_athletes = {
            entry["AthleteKey"]
            for entry in entries
            if str(entry["IsFrench"]) == "1"
        }

        all_size = len(all_athletes)
        french_size = len(french_athletes)

        podium_places = min(3, french_size)

        field_summary.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionName": entries[0][
                    "CompetitionName"
                ],
                "ChampionshipBlock": block,
                "PopulationGroup": population,
                "Category": category,
                "CategoryOrder": category_order,
                "Sex": sex,
                "Event": event,
                "ApprovedAll": all_size,
                "ApprovedFrench": french_size,
                "ApprovedForeign": all_size - french_size,
                "FrenchDepthClass": field_depth_class(
                    french_size
                ),
                "FrenchFieldOneToThree": int(
                    1 <= french_size <= 3
                ),
                "FrenchPodiumPlaces": podium_places,
                "FrenchPodiumWeightPercent": (
                    round(
                        100 * podium_places / french_size,
                        1,
                    )
                    if french_size
                    else 0
                ),
                "RawCategories": " | ".join(
                    sorted(
                        {
                            entry["CategoryRaw"]
                            for entry in entries
                        }
                    )
                ),
                "DivisionLabels": " | ".join(
                    sorted(
                        {
                            entry["Division"]
                            for entry in entries
                            if entry["Division"]
                        }
                    )
                ),
            }
        )

    field_summary.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["ChampionshipBlock"]),
            int(row["CategoryOrder"]),
            str(row["Sex"]),
            str(row["Event"]),
        )
    )

    # ------------------------------------------------------------
    # Synthèse annuelle par bloc de championnat
    # ------------------------------------------------------------

    block_summary: list[dict[str, Any]] = []

    for year, code, block in CHAMPIONSHIPS:
        block_participants = [
            row
            for row in participants
            if (
                row["CompetitionCode"] == code
                and int(row["TitleEligible"]) == 1
            )
        ]

        block_entries = [
            row
            for row in title_field_entries
            if row["CompetitionCode"] == code
        ]

        block_fields = [
            row
            for row in field_summary
            if row["CompetitionCode"] == code
            and int(row["ApprovedFrench"]) > 0
        ]

        french_participants = {
            row["AthleteKey"]
            for row in block_participants
            if str(row["IsFrench"]) == "1"
        }

        french_with_event = {
            row["AthleteKey"]
            for row in block_entries
            if str(row["IsFrench"]) == "1"
        }

        field_sizes = [
            int(row["ApprovedFrench"])
            for row in block_fields
        ]

        field_participations = sum(field_sizes)

        fields_one_to_three = sum(
            1
            for size in field_sizes
            if 1 <= size <= 3
        )

        podium_places = sum(
            min(3, size)
            for size in field_sizes
        )

        block_summary.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "ChampionshipBlock": block,
                "CompetitionName": (
                    block_participants[0]["CompetitionName"]
                    if block_participants
                    else ""
                ),
                "ApprovedFrenchAthletes": len(
                    french_participants
                ),
                "FrenchAthletesWithEvent": len(
                    french_with_event
                ),
                "ObservedFrenchFields": len(block_fields),
                "FrenchFieldParticipations": (
                    field_participations
                ),
                "MeanFrenchFieldSize": (
                    round(
                        statistics.mean(field_sizes),
                        2,
                    )
                    if field_sizes
                    else 0
                ),
                "MedianFrenchFieldSize": (
                    statistics.median(field_sizes)
                    if field_sizes
                    else 0
                ),
                "FieldsOneToThree": fields_one_to_three,
                "ShareFieldsOneToThreePercent": (
                    round(
                        100
                        * fields_one_to_three
                        / len(field_sizes),
                        1,
                    )
                    if field_sizes
                    else 0
                ),
                "FrenchPodiumPlaces": podium_places,
                "FrenchPodiumWeightPercent": (
                    round(
                        100
                        * podium_places
                        / field_participations,
                        1,
                    )
                    if field_participations
                    else 0
                ),
            }
        )

    # ------------------------------------------------------------
    # Synthèse population × sexe × épreuve
    # ------------------------------------------------------------

    dimension_groups: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for field in field_summary:
        if int(field["ApprovedFrench"]) <= 0:
            continue

        key = (
            field["Year"],
            field["ChampionshipBlock"],
            field["PopulationGroup"],
            field["Sex"],
            field["Event"],
        )

        dimension_groups[key].append(field)

    dimension_summary: list[dict[str, Any]] = []

    for key, fields in dimension_groups.items():
        (
            year,
            block,
            population,
            sex,
            event,
        ) = key

        sizes = [
            int(field["ApprovedFrench"])
            for field in fields
        ]

        total = sum(sizes)
        sparse = sum(
            1
            for size in sizes
            if 1 <= size <= 3
        )
        podium_places = sum(
            min(3, size)
            for size in sizes
        )

        dimension_summary.append(
            {
                "Year": year,
                "ChampionshipBlock": block,
                "PopulationGroup": population,
                "Sex": sex,
                "Event": event,
                "ObservedFields": len(fields),
                "FrenchFieldParticipations": total,
                "MeanFieldSize": round(
                    statistics.mean(sizes),
                    2,
                ),
                "MedianFieldSize": statistics.median(
                    sizes
                ),
                "FieldsOneToThree": sparse,
                "ShareFieldsOneToThreePercent": round(
                    100 * sparse / len(fields),
                    1,
                ),
                "PodiumWeightPercent": round(
                    100 * podium_places / total,
                    1,
                ),
            }
        )

    dimension_summary.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["ChampionshipBlock"]),
            str(row["PopulationGroup"]),
            str(row["Sex"]),
            str(row["Event"]),
        )
    )

    # ------------------------------------------------------------
    # Écriture des fichiers
    # ------------------------------------------------------------

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "participants_normalises_2023_2026.csv"
        ),
        participants,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "entrees_champs_2023_2026.csv"
        ),
        field_entries,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "champs_2023_2026.csv"
        ),
        field_summary,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "entrees_paralleles_2023_2026.csv"
        ),
        parallel_field_entries,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "synthese_blocs_2023_2026.csv"
        ),
        block_summary,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "synthese_population_sexe_epreuve_"
            "2023_2026.csv"
        ),
        dimension_summary,
    )

    anomaly_fields = [
        "Year",
        "CompetitionCode",
        "ChampionshipBlock",
        "CompetitionName",
        "AthleteKey",
        "Name",
        "Country",
        "CategoryRaw",
        "AnomalyType",
        "Detail",
    ]

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "anomalies_2023_2026.csv"
        ),
        anomalies,
        fieldnames=anomaly_fields,
    )

    print("=" * 110)
    print(
        "CHAMPIONNATS DE FRANCE — "
        "INSCRIPTIONS APPROUVÉES EMS"
    )
    print("=" * 110)

    header = (
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'Français':>10}"
        f"{'Champs':>9}"
        f"{'Particip.':>11}"
        f"{'Moy.':>8}"
        f"{'Méd.':>8}"
        f"{'1-3':>8}"
        f"{'% 1-3':>9}"
        f"{'Poids podium':>15}"
    )

    print(header)
    print("-" * len(header))

    for row in block_summary:
        print(
            f"{row['Year']:<7}"
            f"{row['ChampionshipBlock']:<12}"
            f"{row['ApprovedFrenchAthletes']:>10}"
            f"{row['ObservedFrenchFields']:>9}"
            f"{row['FrenchFieldParticipations']:>11}"
            f"{row['MeanFrenchFieldSize']:>8}"
            f"{row['MedianFrenchFieldSize']:>8}"
            f"{row['FieldsOneToThree']:>8}"
            f"{row['ShareFieldsOneToThreePercent']:>9}"
            f"{row['FrenchPodiumWeightPercent']:>15}"
        )

    print()
    title_participants = [
        row
        for row in participants
        if int(row["TitleEligible"]) == 1
    ]

    print(f"Participants normalisés : {len(participants)}")
    print(f"Participants éligibles  : {len(title_participants)}")
    print(f"Entrées totales         : {len(field_entries)}")
    print(f"Entrées de titre        : {len(title_field_entries)}")
    print(f"Entrées parallèles      : {len(parallel_field_entries)}")
    print(f"Champs de titre observés: {len(field_summary)}")
    print(f"Anomalies               : {len(anomalies)}")


if __name__ == "__main__":
    main()