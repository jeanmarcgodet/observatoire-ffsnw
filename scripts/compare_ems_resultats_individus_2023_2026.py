"""Compare individuellement les inscriptions EMS et les résultats classés."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EMS_FILE = (
    ROOT
    / "data/processed/"
    / "ems_championnats_france_entrees_champs_2023_2026.csv"
)

RESULT_FILE = (
    ROOT
    / "data/processed/"
    / "resultats_classes_individuels_2023_2026.csv"
)

OUTPUT_FILE = (
    ROOT
    / "data/processed/"
    / "comparaison_ems_resultats_individus_2023_2026.csv"
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
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def person_key(
    row: dict[str, Any],
) -> str:
    return str(
        row.get("AthleteKey", "")
    ).strip()


def main() -> None:
    ems_rows = [
        row
        for row in read_csv(EMS_FILE)
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    result_rows = [
        row
        for row in read_csv(RESULT_FILE)
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    ems_fields: dict[
        tuple[str, ...],
        dict[str, dict[str, str]],
    ] = defaultdict(dict)

    result_fields: dict[
        tuple[str, ...],
        dict[str, dict[str, str]],
    ] = defaultdict(dict)

    for row in ems_rows:
        ems_fields[field_key(row)][
            person_key(row)
        ] = row

    for row in result_rows:
        result_fields[field_key(row)][
            person_key(row)
        ] = row

    all_fields = sorted(
        set(ems_fields)
        | set(result_fields)
    )

    output_rows: list[dict[str, Any]] = []

    for field in all_fields:
        ems_people = ems_fields.get(
            field,
            {},
        )

        result_people = result_fields.get(
            field,
            {},
        )

        all_people = sorted(
            set(ems_people)
            | set(result_people)
        )

        for athlete_key in all_people:
            ems = ems_people.get(
                athlete_key
            )

            result = result_people.get(
                athlete_key
            )

            if ems and result:
                status = "MATCH"
            elif ems:
                status = "EMS_ONLY"
            else:
                status = "RESULTS_ONLY"

            (
                year,
                competition_code,
                block,
                population,
                category,
                sex,
                event,
            ) = field

            source = ems or result or {}

            output_rows.append(
                {
                    "Year": year,
                    "CompetitionCode": competition_code,
                    "ChampionshipBlock": block,
                    "PopulationGroup": population,
                    "Category": category,
                    "Sex": sex,
                    "Event": event,
                    "AthleteKey": athlete_key,
                    "Name": source.get(
                        "Name",
                        "",
                    ),
                    "YOB": source.get(
                        "YOB",
                        "",
                    ),
                    "Status": status,
                    "EmsName": (
                        ems.get("Name", "")
                        if ems
                        else ""
                    ),
                    "ResultName": (
                        result.get("Name", "")
                        if result
                        else ""
                    ),
                    "EmsCategoryRaw": (
                        ems.get(
                            "CategoryRaw",
                            "",
                        )
                        if ems
                        else ""
                    ),
                    "ResultRiderId": (
                        result.get(
                            "RiderId",
                            "",
                        )
                        if result
                        else ""
                    ),
                }
            )

    write_csv(
        OUTPUT_FILE,
        output_rows,
    )

    differences = [
        row
        for row in output_rows
        if row["Status"] != "MATCH"
    ]

    print("=" * 125)
    print(
        "COMPARAISON INDIVIDUELLE EMS / "
        "RÉSULTATS CLASSÉS"
    )
    print("=" * 125)

    print(
        "Lignes comparées :",
        len(output_rows),
    )

    print(
        "Correspondances exactes :",
        sum(
            1
            for row in output_rows
            if row["Status"] == "MATCH"
        ),
    )

    print(
        "EMS uniquement :",
        sum(
            1
            for row in output_rows
            if row["Status"] == "EMS_ONLY"
        ),
    )

    print(
        "Résultats uniquement :",
        sum(
            1
            for row in output_rows
            if row["Status"] == "RESULTS_ONLY"
        ),
    )

    print()
    print(
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'Cat.':<8}"
        f"{'S':<4}"
        f"{'Épreuve':<10}"
        f"{'Statut':<15}"
        f"{'Nom'}"
    )

    print("-" * 115)

    for row in differences:
        print(
            f"{row['Year']:<7}"
            f"{row['ChampionshipBlock']:<12}"
            f"{row['Category']:<8}"
            f"{row['Sex']:<4}"
            f"{row['Event']:<10}"
            f"{row['Status']:<15}"
            f"{row['Name']}"
        )

    print()
    print("CSV :", OUTPUT_FILE)


if __name__ == "__main__":
    main()