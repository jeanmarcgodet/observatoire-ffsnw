"""Réconcilie les identités et qualifie les écarts EMS/résultats."""

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

CANDIDATES_FILE = (
    ROOT
    / "data/processed/"
    / "candidats_identites_ems_resultats_2023_2026.csv"
)

ALIASES_FILE = (
    ROOT
    / "data/reference/"
    / "ems_result_identity_aliases.csv"
)

OUTPUT_FILE = (
    ROOT
    / "data/processed/"
    / "comparaison_ems_resultats_reconciliee_2023_2026.csv"
)

OUTPUT_DIFFERENCES = (
    ROOT
    / "data/processed/"
    / "ecarts_ems_resultats_reconcilies_2023_2026.csv"
)

ACCEPTED_CONFIDENCE = {
    "AUTO_EXACT_NAME",
    "AUTO_STRONG",
}

INCOMPLETE_RESULT_CODES = {
    "25FRA206",
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


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def make_athlete_key(
    country: str,
    yob: str,
    normalized_name: str,
) -> str:
    return (
        f"{country.strip().upper()}|"
        f"{yob.strip()}|"
        f"{normalized_name.strip().upper()}"
    )


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


def base_key(
    field: tuple[str, ...],
    athlete_key: str,
) -> tuple[str, ...]:
    return (
        field[0],
        field[1],
        field[2],
        field[5],
        field[6],
        athlete_key,
    )


def data_quality(code: str) -> str:
    if code in INCOMPLETE_RESULT_CODES:
        return "RESULTS_INCOMPLETE_SUSPECTED"

    return "USABLE"


def main() -> None:
    all_ems_rows = read_csv(
        EMS_FILE
    )

    all_result_rows = read_csv(
        RESULT_FILE
    )

    ems_rows = [
        row
        for row in all_ems_rows
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    result_rows = [
        row
        for row in all_result_rows
        if (
            as_int(row.get("TitleEligible")) == 1
            and as_int(row.get("IsFrench")) == 1
        )
    ]

    candidates = read_csv(
        CANDIDATES_FILE
    )

    accepted_candidates = [
        row
        for row in candidates
        if row.get("Confidence")
        in ACCEPTED_CONFIDENCE
    ]

    ems_identity_index: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    result_identity_index: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    for row in ems_rows:
        athlete_key = str(
            row.get("AthleteKey", "")
        ).strip()

        parts = athlete_key.split("|")

        yob = (
            parts[1].strip()
            if len(parts) >= 2
            else ""
        )

        identity = (
            str(row.get("Name", "")).strip(),
            yob,
        )

        ems_identity_index[
            identity
        ].add(
            athlete_key
        )

    for row in result_rows:
        athlete_key = str(
            row.get("AthleteKey", "")
        ).strip()

        identity = (
            str(row.get("Name", "")).strip(),
            str(row.get("YOB", "")).strip(),
        )

        result_identity_index[
            identity
        ].add(
            athlete_key
        )

    alias_rows: list[dict[str, Any]] = []
    result_aliases: dict[str, str] = {}

    for row in accepted_candidates:
        ems_identity = (
            str(row.get("EmsName", "")).strip(),
            str(row.get("EmsYOB", "")).strip(),
        )

        result_identity = (
            str(row.get("ResultName", "")).strip(),
            str(row.get("ResultYOB", "")).strip(),
        )

        ems_keys = ems_identity_index.get(
            ems_identity,
            set(),
        )

        result_keys = result_identity_index.get(
            result_identity,
            set(),
        )

        if len(ems_keys) != 1:
            raise RuntimeError(
                "Identit? EMS non univoque : "
                f"{ems_identity} -> "
                f"{sorted(ems_keys)}"
            )

        if len(result_keys) != 1:
            raise RuntimeError(
                "Identit? r?sultat non univoque : "
                f"{result_identity} -> "
                f"{sorted(result_keys)}"
            )

        canonical_key = next(
            iter(ems_keys)
        )

        result_key = next(
            iter(result_keys)
        )

        result_aliases[
            result_key
        ] = canonical_key

        alias_rows.append(
            {
                "ResultAthleteKey": result_key,
                "CanonicalAthleteKey": (
                    canonical_key
                ),
                "EmsName": row.get(
                    "EmsName",
                    "",
                ),
                "ResultName": row.get(
                    "ResultName",
                    "",
                ),
                "Confidence": row.get(
                    "Confidence",
                    "",
                ),
                "NameScore": row.get(
                    "NameScore",
                    "",
                ),
                "Occurrences": row.get(
                    "Occurrences",
                    "",
                ),
            }
        )

    write_csv(
        ALIASES_FILE,
        alias_rows,
        fieldnames=[
            "ResultAthleteKey",
            "CanonicalAthleteKey",
            "EmsName",
            "ResultName",
            "Confidence",
            "NameScore",
            "Occurrences",
        ],
    )

    ems_index: dict[
        tuple[tuple[str, ...], str],
        dict[str, str],
    ] = {}

    result_index: dict[
        tuple[tuple[str, ...], str],
        dict[str, str],
    ] = {}

    for row in ems_rows:
        athlete_key = str(
            row.get("AthleteKey", "")
        ).strip()

        ems_index[
            (
                field_key(row),
                athlete_key,
            )
        ] = row

    for row in result_rows:
        original_key = str(
            row.get("AthleteKey", "")
        ).strip()

        canonical_key = result_aliases.get(
            original_key,
            original_key,
        )

        result_index[
            (
                field_key(row),
                canonical_key,
            )
        ] = row

    exact_keys = (
        set(ems_index)
        & set(result_index)
    )

    unmatched_ems_keys = (
        set(ems_index)
        - exact_keys
    )

    unmatched_result_keys = (
        set(result_index)
        - exact_keys
    )

    exact_categories: dict[
        tuple[str, ...],
        set[str],
    ] = defaultdict(set)

    output_rows: list[dict[str, Any]] = []

    for field, athlete_key in sorted(
        exact_keys
    ):
        ems = ems_index[
            (field, athlete_key)
        ]

        result = result_index[
            (field, athlete_key)
        ]

        base = base_key(
            field,
            athlete_key,
        )

        exact_categories[base].add(
            field[4]
        )

        output_rows.append(
            {
                "Year": field[0],
                "CompetitionCode": field[1],
                "ChampionshipBlock": field[2],
                "Sex": field[5],
                "Event": field[6],
                "CanonicalAthleteKey": athlete_key,
                "Status": "MATCH",
                "DataQuality": data_quality(
                    field[1]
                ),
                "EmsPopulationGroup": field[3],
                "ResultPopulationGroup": field[3],
                "EmsCategory": field[4],
                "ResultCategory": field[4],
                "EmsName": ems.get(
                    "Name",
                    "",
                ),
                "ResultName": result.get(
                    "Name",
                    "",
                ),
            }
        )

    unmatched_ems: dict[
        tuple[str, ...],
        list[
            tuple[
                tuple[str, ...],
                dict[str, str],
            ]
        ],
    ] = defaultdict(list)

    unmatched_results: dict[
        tuple[str, ...],
        list[
            tuple[
                tuple[str, ...],
                dict[str, str],
            ]
        ],
    ] = defaultdict(list)

    for field, athlete_key in (
        unmatched_ems_keys
    ):
        unmatched_ems[
            base_key(
                field,
                athlete_key,
            )
        ].append(
            (
                field,
                ems_index[
                    (field, athlete_key)
                ],
            )
        )

    for field, athlete_key in (
        unmatched_result_keys
    ):
        unmatched_results[
            base_key(
                field,
                athlete_key,
            )
        ].append(
            (
                field,
                result_index[
                    (field, athlete_key)
                ],
            )
        )

    all_residual_bases = sorted(
        set(unmatched_ems)
        | set(unmatched_results)
    )

    category_changes = 0

    for base in all_residual_bases:
        ems_items = unmatched_ems.get(
            base,
            [],
        )

        result_items = (
            unmatched_results.get(
                base,
                [],
            )
        )

        athlete_key = base[5]

        if (
            len(ems_items) == 1
            and len(result_items) == 1
        ):
            ems_field, ems = ems_items[0]
            result_field, result = (
                result_items[0]
            )

            category_changes += 1

            output_rows.append(
                {
                    "Year": base[0],
                    "CompetitionCode": base[1],
                    "ChampionshipBlock": base[2],
                    "Sex": base[3],
                    "Event": base[4],
                    "CanonicalAthleteKey": (
                        athlete_key
                    ),
                    "Status": "CATEGORY_CHANGED",
                    "DataQuality": data_quality(
                        base[1]
                    ),
                    "EmsPopulationGroup": (
                        ems_field[3]
                    ),
                    "ResultPopulationGroup": (
                        result_field[3]
                    ),
                    "EmsCategory": ems_field[4],
                    "ResultCategory": (
                        result_field[4]
                    ),
                    "EmsName": ems.get(
                        "Name",
                        "",
                    ),
                    "ResultName": result.get(
                        "Name",
                        "",
                    ),
                }
            )

            continue

        exact_other_category = (
            exact_categories.get(
                base,
                set(),
            )
        )

        complex_mismatch = bool(
            ems_items
            and result_items
        )

        for field, ems in ems_items:
            if complex_mismatch:
                status = (
                    "CATEGORY_MISMATCH_COMPLEX"
                )
            elif exact_other_category:
                status = (
                    "EMS_ADDITIONAL_CATEGORY"
                )
            else:
                status = "EMS_ONLY"

            output_rows.append(
                {
                    "Year": field[0],
                    "CompetitionCode": field[1],
                    "ChampionshipBlock": (
                        field[2]
                    ),
                    "Sex": field[5],
                    "Event": field[6],
                    "CanonicalAthleteKey": (
                        athlete_key
                    ),
                    "Status": status,
                    "DataQuality": data_quality(
                        field[1]
                    ),
                    "EmsPopulationGroup": (
                        field[3]
                    ),
                    "ResultPopulationGroup": "",
                    "EmsCategory": field[4],
                    "ResultCategory": "",
                    "EmsName": ems.get(
                        "Name",
                        "",
                    ),
                    "ResultName": "",
                }
            )

        for field, result in result_items:
            if complex_mismatch:
                status = (
                    "CATEGORY_MISMATCH_COMPLEX"
                )
            elif exact_other_category:
                status = (
                    "RESULT_ADDITIONAL_CATEGORY"
                )
            else:
                status = "RESULTS_ONLY"

            output_rows.append(
                {
                    "Year": field[0],
                    "CompetitionCode": field[1],
                    "ChampionshipBlock": (
                        field[2]
                    ),
                    "Sex": field[5],
                    "Event": field[6],
                    "CanonicalAthleteKey": (
                        athlete_key
                    ),
                    "Status": status,
                    "DataQuality": data_quality(
                        field[1]
                    ),
                    "EmsPopulationGroup": "",
                    "ResultPopulationGroup": (
                        field[3]
                    ),
                    "EmsCategory": "",
                    "ResultCategory": field[4],
                    "EmsName": "",
                    "ResultName": result.get(
                        "Name",
                        "",
                    ),
                }
            )

    output_rows.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["CompetitionCode"]),
            str(row["ChampionshipBlock"]),
            str(row["Status"]),
            str(row["EmsCategory"]),
            str(row["ResultCategory"]),
            str(row["EmsName"]),
            str(row["ResultName"]),
        )
    )

    differences = [
        row
        for row in output_rows
        if row["Status"] != "MATCH"
    ]

    write_csv(
        OUTPUT_FILE,
        output_rows,
    )

    write_csv(
        OUTPUT_DIFFERENCES,
        differences,
        fieldnames=list(
            output_rows[0].keys()
        ),
    )

    print("=" * 125)
    print(
        "COMPARAISON EMS / RÉSULTATS "
        "APRÈS RÉCONCILIATION"
    )
    print("=" * 125)

    print(
        "Alias d'identité validés       :",
        len(alias_rows),
    )

    print(
        "Correspondances exactes finales :",
        len(exact_keys),
    )

    print(
        "Occurrences résiduelles avant "
        "qualification :",
        (
            len(unmatched_ems_keys)
            + len(unmatched_result_keys)
        ),
    )

    print(
        "Changements de catégorie       :",
        category_changes,
    )

    print()
    print("RÉPARTITION FINALE DES STATUTS")

    status_counts: dict[str, int] = (
        defaultdict(int)
    )

    for row in output_rows:
        status_counts[
            str(row["Status"])
        ] += 1

    for status in sorted(
        status_counts
    ):
        print(
            f"{status:<32}: "
            f"{status_counts[status]:>4}"
        )

    print()
    print(
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'Statut':<30}"
        f"{'Nombre':>8}"
    )
    print("-" * 60)

    grouped_counts: dict[
        tuple[str, str, str],
        int,
    ] = defaultdict(int)

    for row in differences:
        key = (
            str(row["Year"]),
            str(row["ChampionshipBlock"]),
            str(row["Status"]),
        )

        grouped_counts[key] += 1

    for key in sorted(
        grouped_counts
    ):
        print(
            f"{key[0]:<7}"
            f"{key[1]:<12}"
            f"{key[2]:<30}"
            f"{grouped_counts[key]:>8}"
        )

    print()
    print("Alias       :", ALIASES_FILE)
    print("Comparaison :", OUTPUT_FILE)
    print("Écarts      :", OUTPUT_DIFFERENCES)


if __name__ == "__main__":
    main()