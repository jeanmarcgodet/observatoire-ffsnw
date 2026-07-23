"""Compare les inscriptions EMS et les résultats classés par champ."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EMS_FIELDS_FILE = (
    ROOT
    / "data/processed/"
    / "ems_championnats_france_champs_2023_2026.csv"
)

RESULT_FIELDS_FILE = (
    ROOT
    / "data/processed/"
    / "resultats_classes_champs_2023_2026.csv"
)

EMS_PARTICIPANTS_FILE = (
    ROOT
    / "data/processed/"
    / "ems_championnats_france_participants_normalises_2023_2026.csv"
)

RESULT_PARTICIPANTS_FILE = (
    ROOT
    / "data/processed/"
    / "resultats_classes_individuels_2023_2026.csv"
)

OUTPUT_FIELDS_FILE = (
    ROOT
    / "data/processed/"
    / "comparaison_ems_resultats_champs_2023_2026.csv"
)

OUTPUT_BLOCKS_FILE = (
    ROOT
    / "data/processed/"
    / "comparaison_ems_resultats_blocs_2023_2026.csv"
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


def field_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    return (
        str(row.get("Year", "")),
        str(row.get("CompetitionCode", "")),
        str(row.get("ChampionshipBlock", "")),
        str(row.get("PopulationGroup", "")),
        str(row.get("Category", "")),
        str(row.get("Sex", "")),
        str(row.get("Event", "")),
    )


def comparison_status(
    approved: int,
    classified: int,
) -> str:
    if approved == classified:
        return "MATCH"

    if approved == 0 and classified > 0:
        return "RESULTS_ONLY"

    if approved > 0 and classified == 0:
        return "EMS_ONLY"

    if classified < approved:
        return "CLASSIFIED_LOWER"

    return "CLASSIFIED_HIGHER"


def quality_status(
    approved_entries: int,
    classified_entries: int,
    approved_fields: int,
    classified_fields: int,
) -> str:
    if (
        approved_entries == classified_entries
        and approved_fields == classified_fields
    ):
        return "EXACT"

    if (
        abs(approved_entries - classified_entries) <= 2
        and abs(approved_fields - classified_fields) <= 1
    ):
        return "CLOSE"

    entry_coverage = (
        classified_entries / approved_entries
        if approved_entries
        else 1
    )

    field_coverage = (
        classified_fields / approved_fields
        if approved_fields
        else 1
    )

    if (
        entry_coverage < 0.75
        or field_coverage < 0.75
    ):
        return "RESULTS_INCOMPLETE_SUSPECTED"

    return "REVIEW"


def main() -> None:
    ems_fields = [
        row
        for row in read_csv(EMS_FIELDS_FILE)
        if as_int(row.get("ApprovedFrench")) > 0
    ]

    result_fields = [
        row
        for row in read_csv(RESULT_FIELDS_FILE)
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("ClassifiedFrench")) > 0
        )
    ]

    ems_lookup = {
        field_key(row): row
        for row in ems_fields
    }

    result_lookup = {
        field_key(row): row
        for row in result_fields
    }

    all_keys = sorted(
        set(ems_lookup)
        | set(result_lookup)
    )

    comparison_rows: list[dict[str, Any]] = []

    for key in all_keys:
        ems = ems_lookup.get(key, {})
        result = result_lookup.get(key, {})

        approved = as_int(
            ems.get("ApprovedFrench")
        )

        classified = as_int(
            result.get("ClassifiedFrench")
        )

        (
            year,
            competition_code,
            block,
            population,
            category,
            sex,
            event,
        ) = key

        comparison_rows.append(
            {
                "Year": year,
                "CompetitionCode": competition_code,
                "ChampionshipBlock": block,
                "PopulationGroup": population,
                "Category": category,
                "Sex": sex,
                "Event": event,
                "ApprovedFrench": approved,
                "ClassifiedFrench": classified,
                "DifferenceClassifiedMinusApproved": (
                    classified - approved
                ),
                "ClassificationCoveragePercent": (
                    round(
                        100 * classified / approved,
                        1,
                    )
                    if approved
                    else ""
                ),
                "Status": comparison_status(
                    approved,
                    classified,
                ),
            }
        )

    ems_participants = [
        row
        for row in read_csv(
            EMS_PARTICIPANTS_FILE
        )
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    result_participants = [
        row
        for row in read_csv(
            RESULT_PARTICIPANTS_FILE
        )
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    ems_athletes: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    result_athletes: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    for row in ems_participants:
        key = (
            str(row["Year"]),
            str(row["ChampionshipBlock"]),
        )

        ems_athletes[key].add(
            str(row["AthleteKey"])
        )

    for row in result_participants:
        key = (
            str(row["Year"]),
            str(row["ChampionshipBlock"]),
        )

        result_athletes[key].add(
            str(row["RiderId"])
        )

    block_groups: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in comparison_rows:
        key = (
            str(row["Year"]),
            str(row["ChampionshipBlock"]),
        )

        block_groups[key].append(row)

    block_rows: list[dict[str, Any]] = []

    for key, rows in sorted(
        block_groups.items()
    ):
        year, block = key

        approved_entries = sum(
            as_int(row["ApprovedFrench"])
            for row in rows
        )

        classified_entries = sum(
            as_int(row["ClassifiedFrench"])
            for row in rows
        )

        approved_fields = sum(
            1
            for row in rows
            if as_int(row["ApprovedFrench"]) > 0
        )

        classified_fields = sum(
            1
            for row in rows
            if as_int(row["ClassifiedFrench"]) > 0
        )

        shared_fields = sum(
            1
            for row in rows
            if (
                as_int(row["ApprovedFrench"]) > 0
                and as_int(row["ClassifiedFrench"]) > 0
            )
        )

        ems_only_fields = sum(
            1
            for row in rows
            if row["Status"] == "EMS_ONLY"
        )

        results_only_fields = sum(
            1
            for row in rows
            if row["Status"] == "RESULTS_ONLY"
        )

        block_rows.append(
            {
                "Year": year,
                "ChampionshipBlock": block,
                "ApprovedFrenchAthletes": len(
                    ems_athletes.get(key, set())
                ),
                "ClassifiedFrenchAthletes": len(
                    result_athletes.get(key, set())
                ),
                "ApprovedFrenchFieldEntries": (
                    approved_entries
                ),
                "ClassifiedFrenchFieldEntries": (
                    classified_entries
                ),
                "EntryDifference": (
                    classified_entries
                    - approved_entries
                ),
                "EntryCoveragePercent": (
                    round(
                        100
                        * classified_entries
                        / approved_entries,
                        1,
                    )
                    if approved_entries
                    else ""
                ),
                "ApprovedFields": approved_fields,
                "ClassifiedFields": classified_fields,
                "SharedFields": shared_fields,
                "EmsOnlyFields": ems_only_fields,
                "ResultsOnlyFields": (
                    results_only_fields
                ),
                "QualityStatus": quality_status(
                    approved_entries,
                    classified_entries,
                    approved_fields,
                    classified_fields,
                ),
            }
        )

    write_csv(
        OUTPUT_FIELDS_FILE,
        comparison_rows,
    )

    write_csv(
        OUTPUT_BLOCKS_FILE,
        block_rows,
    )

    print("=" * 120)
    print(
        "COMPARAISON EMS / RÉSULTATS CLASSÉS "
        "— CHAMPIONNATS DE FRANCE"
    )
    print("=" * 120)

    print(
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'EMS':>7}"
        f"{'Classés':>9}"
        f"{'Part. EMS':>11}"
        f"{'Part. cl.':>11}"
        f"{'Ch. EMS':>9}"
        f"{'Ch. cl.':>9}"
        f"{'Qualité':>30}"
    )

    print("-" * 105)

    for row in block_rows:
        print(
            f"{row['Year']:<7}"
            f"{row['ChampionshipBlock']:<12}"
            f"{row['ApprovedFrenchAthletes']:>7}"
            f"{row['ClassifiedFrenchAthletes']:>9}"
            f"{row['ApprovedFrenchFieldEntries']:>11}"
            f"{row['ClassifiedFrenchFieldEntries']:>11}"
            f"{row['ApprovedFields']:>9}"
            f"{row['ClassifiedFields']:>9}"
            f"{row['QualityStatus']:>30}"
        )

    print()
    print("Fichier champs :", OUTPUT_FIELDS_FILE)
    print("Fichier blocs  :", OUTPUT_BLOCKS_FILE)


if __name__ == "__main__":
    main()