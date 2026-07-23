"""Analyse la conversion des inscriptions EMS en classements."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    ROOT
    / "data/processed/"
    / "comparaison_ems_resultats_reconciliee_2023_2026.csv"
)

ATHLETE_OUTPUT_FILE = (
    ROOT
    / "data/processed/"
    / "conversion_ems_resultats_par_sportif_2023_2026.csv"
)

SUMMARY_OUTPUT_FILE = (
    ROOT
    / "data/processed/"
    / "conversion_ems_resultats_par_bloc_2023_2026.csv"
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


def athlete_status(
    approved_fields: int,
    classified_fields: int,
    matched_fields: int,
    missing_fields: int,
) -> str:
    if approved_fields == 0:
        if classified_fields > 0:
            return "RESULTS_ONLY"

        return "NO_DATA"

    if classified_fields == 0:
        return "NO_CLASSIFICATION"

    if missing_fields == 0:
        return "FULL_CONVERSION"

    if matched_fields > 0:
        return "PARTIAL_CONVERSION"

    return "CLASSIFIED_WITHOUT_MATCH"


def main() -> None:
    rows = [
        row
        for row in read_csv(SOURCE_FILE)
        if row.get("DataQuality") == "USABLE"
    ]

    athlete_groups: dict[
        tuple[str, str, str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in rows:
        key = (
            str(row.get("Year", "")),
            str(row.get("CompetitionCode", "")),
            str(row.get("ChampionshipBlock", "")),
            str(
                row.get(
                    "CanonicalAthleteKey",
                    "",
                )
            ),
        )

        athlete_groups[key].append(row)

    athlete_rows: list[dict[str, Any]] = []

    for key, athlete_data in athlete_groups.items():
        (
            year,
            competition_code,
            block,
            athlete_key,
        ) = key

        ems_names = sorted(
            {
                str(row.get("EmsName", "")).strip()
                for row in athlete_data
                if str(
                    row.get("EmsName", "")
                ).strip()
            }
        )

        result_names = sorted(
            {
                str(
                    row.get(
                        "ResultName",
                        "",
                    )
                ).strip()
                for row in athlete_data
                if str(
                    row.get(
                        "ResultName",
                        "",
                    )
                ).strip()
            }
        )

        display_name = (
            ems_names[0]
            if ems_names
            else (
                result_names[0]
                if result_names
                else athlete_key
            )
        )

        approved_rows = [
            row
            for row in athlete_data
            if str(
                row.get(
                    "EmsCategory",
                    "",
                )
            ).strip()
        ]

        classified_rows = [
            row
            for row in athlete_data
            if str(
                row.get(
                    "ResultCategory",
                    "",
                )
            ).strip()
        ]

        matched_rows = [
            row
            for row in athlete_data
            if row.get("Status")
            in {
                "MATCH",
                "CATEGORY_CHANGED",
            }
        ]

        missing_rows = [
            row
            for row in athlete_data
            if row.get("Status")
            == "EMS_ONLY"
        ]

        additional_rows = [
            row
            for row in athlete_data
            if row.get("Status")
            in {
                "RESULTS_ONLY",
                "RESULT_ADDITIONAL_CATEGORY",
            }
        ]

        changed_rows = [
            row
            for row in athlete_data
            if row.get("Status")
            == "CATEGORY_CHANGED"
        ]

        approved_fields = len(
            approved_rows
        )

        classified_fields = len(
            classified_rows
        )

        matched_fields = len(
            matched_rows
        )

        missing_fields = len(
            missing_rows
        )

        additional_fields = len(
            additional_rows
        )

        status = athlete_status(
            approved_fields,
            classified_fields,
            matched_fields,
            missing_fields,
        )

        athlete_rows.append(
            {
                "Year": year,
                "CompetitionCode": competition_code,
                "ChampionshipBlock": block,
                "AthleteKey": athlete_key,
                "Name": display_name,
                "Sex": ", ".join(
                    sorted(
                        {
                            str(
                                row.get(
                                    "Sex",
                                    "",
                                )
                            ).strip()
                            for row in athlete_data
                            if str(
                                row.get(
                                    "Sex",
                                    "",
                                )
                            ).strip()
                        }
                    )
                ),
                "ConversionStatus": status,
                "ApprovedFields": approved_fields,
                "MatchedApprovedFields": (
                    matched_fields
                ),
                "MissingApprovedFields": (
                    missing_fields
                ),
                "ClassifiedFields": (
                    classified_fields
                ),
                "AdditionalResultFields": (
                    additional_fields
                ),
                "CategoryChanges": len(
                    changed_rows
                ),
                "FieldConversionPercent": (
                    round(
                        100
                        * matched_fields
                        / approved_fields,
                        1,
                    )
                    if approved_fields
                    else ""
                ),
                "ApprovedEvents": ", ".join(
                    sorted(
                        {
                            str(
                                row.get(
                                    "Event",
                                    "",
                                )
                            )
                            for row in approved_rows
                        }
                    )
                ),
                "MissingEvents": ", ".join(
                    sorted(
                        {
                            str(
                                row.get(
                                    "Event",
                                    "",
                                )
                            )
                            for row in missing_rows
                        }
                    )
                ),
                "EmsCategories": ", ".join(
                    sorted(
                        {
                            str(
                                row.get(
                                    "EmsCategory",
                                    "",
                                )
                            )
                            for row in approved_rows
                        }
                    )
                ),
                "ResultCategories": ", ".join(
                    sorted(
                        {
                            str(
                                row.get(
                                    "ResultCategory",
                                    "",
                                )
                            )
                            for row in classified_rows
                        }
                    )
                ),
            }
        )

    athlete_rows.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["ChampionshipBlock"]),
            str(row["ConversionStatus"]),
            str(row["Name"]),
        )
    )

    block_groups: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in athlete_rows:
        key = (
            str(row["Year"]),
            str(row["CompetitionCode"]),
            str(row["ChampionshipBlock"]),
        )

        block_groups[key].append(row)

    summary_rows: list[dict[str, Any]] = []

    for key, block_data in sorted(
        block_groups.items()
    ):
        (
            year,
            competition_code,
            block,
        ) = key

        approved_athletes = [
            row
            for row in block_data
            if int(
                row["ApprovedFields"]
            ) > 0
        ]

        full_athletes = [
            row
            for row in approved_athletes
            if row["ConversionStatus"]
            == "FULL_CONVERSION"
        ]

        partial_athletes = [
            row
            for row in approved_athletes
            if row["ConversionStatus"]
            == "PARTIAL_CONVERSION"
        ]

        no_classification_athletes = [
            row
            for row in approved_athletes
            if row["ConversionStatus"]
            == "NO_CLASSIFICATION"
        ]

        approved_fields = sum(
            int(row["ApprovedFields"])
            for row in approved_athletes
        )

        matched_fields = sum(
            int(
                row[
                    "MatchedApprovedFields"
                ]
            )
            for row in approved_athletes
        )

        missing_fields = sum(
            int(
                row[
                    "MissingApprovedFields"
                ]
            )
            for row in approved_athletes
        )

        summary_rows.append(
            {
                "Year": year,
                "CompetitionCode": (
                    competition_code
                ),
                "ChampionshipBlock": block,
                "ApprovedAthletes": len(
                    approved_athletes
                ),
                "AthletesWithAnyClassification": (
                    len(approved_athletes)
                    - len(
                        no_classification_athletes
                    )
                ),
                "FullConversionAthletes": len(
                    full_athletes
                ),
                "PartialConversionAthletes": len(
                    partial_athletes
                ),
                "NoClassificationAthletes": len(
                    no_classification_athletes
                ),
                "AthleteClassificationRatePercent": (
                    round(
                        100
                        * (
                            len(approved_athletes)
                            - len(
                                no_classification_athletes
                            )
                        )
                        / len(approved_athletes),
                        1,
                    )
                    if approved_athletes
                    else ""
                ),
                "FullConversionRatePercent": (
                    round(
                        100
                        * len(full_athletes)
                        / len(approved_athletes),
                        1,
                    )
                    if approved_athletes
                    else ""
                ),
                "ApprovedFieldEntries": (
                    approved_fields
                ),
                "MatchedApprovedFieldEntries": (
                    matched_fields
                ),
                "MissingApprovedFieldEntries": (
                    missing_fields
                ),
                "FieldConversionRatePercent": (
                    round(
                        100
                        * matched_fields
                        / approved_fields,
                        1,
                    )
                    if approved_fields
                    else ""
                ),
            }
        )

    write_csv(
        ATHLETE_OUTPUT_FILE,
        athlete_rows,
    )

    write_csv(
        SUMMARY_OUTPUT_FILE,
        summary_rows,
    )

    print("=" * 135)
    print(
        "CONVERSION DES INSCRIPTIONS EMS "
        "EN RÉSULTATS CLASSÉS"
    )
    print("=" * 135)

    print(
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'Inscrits':>10}"
        f"{'Classés':>10}"
        f"{'Complets':>10}"
        f"{'Partiels':>10}"
        f"{'Sans cl.':>10}"
        f"{'Champs':>10}"
        f"{'Convertis':>11}"
        f"{'Taux champ':>12}"
    )
    print("-" * 115)

    for row in summary_rows:
        print(
            f"{row['Year']:<7}"
            f"{row['ChampionshipBlock']:<12}"
            f"{row['ApprovedAthletes']:>10}"
            f"{row['AthletesWithAnyClassification']:>10}"
            f"{row['FullConversionAthletes']:>10}"
            f"{row['PartialConversionAthletes']:>10}"
            f"{row['NoClassificationAthletes']:>10}"
            f"{row['ApprovedFieldEntries']:>10}"
            f"{row['MatchedApprovedFieldEntries']:>11}"
            f"{float(row['FieldConversionRatePercent']):>11.1f}%"
        )

    print()
    print("=" * 135)
    print(
        "SPORTIFS AVEC CONVERSION PARTIELLE "
        "OU SANS CLASSEMENT"
    )
    print("=" * 135)

    incomplete_athletes = [
        row
        for row in athlete_rows
        if row["ConversionStatus"]
        in {
            "PARTIAL_CONVERSION",
            "NO_CLASSIFICATION",
        }
    ]

    if not incomplete_athletes:
        print("Aucun cas.")
    else:
        print(
            f"{'Année':<7}"
            f"{'Bloc':<12}"
            f"{'Statut':<23}"
            f"{'Nom':<30}"
            f"{'Inscr.':>7}"
            f"{'Manq.':>7}  "
            f"{'Épreuves manquantes'}"
        )
        print("-" * 120)

        for row in incomplete_athletes:
            print(
                f"{row['Year']:<7}"
                f"{row['ChampionshipBlock']:<12}"
                f"{row['ConversionStatus']:<23}"
                f"{row['Name']:<30}"
                f"{row['ApprovedFields']:>7}"
                f"{row['MissingApprovedFields']:>7}  "
                f"{row['MissingEvents']}"
            )

    print()
    print("Par sportif :", ATHLETE_OUTPUT_FILE)
    print("Par bloc    :", SUMMARY_OUTPUT_FILE)


if __name__ == "__main__":
    main()