"""Vérifie l'application effective des alias EMS/résultats."""

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

ACCEPTED_CONFIDENCE = {
    "AUTO_EXACT_NAME",
    "AUTO_STRONG",
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

    candidates = [
        row
        for row in read_csv(CANDIDATES_FILE)
        if row.get("Confidence")
        in ACCEPTED_CONFIDENCE
    ]

    ems_fields_by_identity: dict[
        str,
        set[tuple[str, ...]],
    ] = defaultdict(set)

    result_fields_by_identity: dict[
        str,
        set[tuple[str, ...]],
    ] = defaultdict(set)

    for row in ems_rows:
        ems_fields_by_identity[
            str(row["AthleteKey"]).strip()
        ].add(
            field_key(row)
        )

    for row in result_rows:
        result_fields_by_identity[
            str(row["AthleteKey"]).strip()
        ].add(
            field_key(row)
        )

    alias_targets: dict[
        str,
        set[str],
    ] = defaultdict(set)

    canonical_sources: dict[
        str,
        set[str],
    ] = defaultdict(set)

    audit_rows = []

    for row in candidates:
        result_key = make_athlete_key(
            "FRA",
            str(row.get("ResultYOB", "")),
            str(
                row.get(
                    "ResultNormalizedName",
                    "",
                )
            ),
        )

        canonical_key = make_athlete_key(
            "FRA",
            str(row.get("EmsYOB", "")),
            str(
                row.get(
                    "EmsNormalizedName",
                    "",
                )
            ),
        )

        alias_targets[result_key].add(
            canonical_key
        )

        canonical_sources[canonical_key].add(
            result_key
        )

        ems_fields = (
            ems_fields_by_identity.get(
                canonical_key,
                set(),
            )
        )

        result_fields = (
            result_fields_by_identity.get(
                result_key,
                set(),
            )
        )

        common_fields = (
            ems_fields
            & result_fields
        )

        expected = as_int(
            row.get("Occurrences")
        )

        audit_rows.append(
            {
                "EmsName": row.get(
                    "EmsName",
                    "",
                ),
                "ResultName": row.get(
                    "ResultName",
                    "",
                ),
                "EmsYOB": row.get(
                    "EmsYOB",
                    "",
                ),
                "ResultYOB": row.get(
                    "ResultYOB",
                    "",
                ),
                "ExpectedOccurrences": expected,
                "CommonFieldsFound": len(
                    common_fields
                ),
                "Difference": (
                    len(common_fields)
                    - expected
                ),
                "EmsFieldsTotal": len(
                    ems_fields
                ),
                "ResultFieldsTotal": len(
                    result_fields
                ),
                "ResultKey": result_key,
                "CanonicalKey": canonical_key,
            }
        )

    original_ems_keys = {
        (
            field_key(row),
            str(row["AthleteKey"]).strip(),
        )
        for row in ems_rows
    }

    original_result_keys = {
        (
            field_key(row),
            str(row["AthleteKey"]).strip(),
        )
        for row in result_rows
    }

    original_matches = len(
        original_ems_keys
        & original_result_keys
    )

    result_alias_map = {}

    for row in candidates:
        result_key = make_athlete_key(
            "FRA",
            str(row.get("ResultYOB", "")),
            str(
                row.get(
                    "ResultNormalizedName",
                    "",
                )
            ),
        )

        canonical_key = make_athlete_key(
            "FRA",
            str(row.get("EmsYOB", "")),
            str(
                row.get(
                    "EmsNormalizedName",
                    "",
                )
            ),
        )

        result_alias_map[result_key] = (
            canonical_key
        )

    reconciled_result_keys = {
        (
            field_key(row),
            result_alias_map.get(
                str(row["AthleteKey"]).strip(),
                str(row["AthleteKey"]).strip(),
            ),
        )
        for row in result_rows
    }

    reconciled_matches = len(
        original_ems_keys
        & reconciled_result_keys
    )

    print("=" * 125)
    print("AUDIT DE L'APPLICATION DES ALIAS")
    print("=" * 125)

    print(
        "Correspondances initiales       :",
        original_matches,
    )

    print(
        "Occurrences proposées           :",
        sum(
            as_int(row.get("Occurrences"))
            for row in candidates
        ),
    )

    print(
        "Correspondances après alias     :",
        reconciled_matches,
    )

    print(
        "Gain effectif                   :",
        reconciled_matches
        - original_matches,
    )

    print(
        "Gain théorique                  :",
        sum(
            as_int(row.get("Occurrences"))
            for row in candidates
        ),
    )

    print()
    print("=" * 125)
    print("PAIRES DONT LE NOMBRE D'OCCURRENCES DIFFÈRE")
    print("=" * 125)

    discrepancies = [
        row
        for row in audit_rows
        if row["Difference"] != 0
    ]

    if not discrepancies:
        print("Aucune différence.")
    else:
        print(
            f"{'EMS':<34}"
            f"{'Résultats':<30}"
            f"{'Att.':>6}"
            f"{'Trouv.':>8}"
            f"{'Écart':>7}"
            f"{'YOB EMS':>10}"
            f"{'YOB Rés.':>10}"
        )
        print("-" * 115)

        for row in sorted(
            discrepancies,
            key=lambda item: (
                item["Difference"],
                item["EmsName"],
            ),
        ):
            print(
                f"{str(row['EmsName']):<34}"
                f"{str(row['ResultName']):<30}"
                f"{row['ExpectedOccurrences']:>6}"
                f"{row['CommonFieldsFound']:>8}"
                f"{row['Difference']:>7}"
                f"{str(row['EmsYOB']):>10}"
                f"{str(row['ResultYOB']):>10}"
            )

    print()
    print("=" * 125)
    print("COLLISIONS : UNE CLÉ RÉSULTAT VERS PLUSIEURS IDENTITÉS EMS")
    print("=" * 125)

    result_collisions = {
        key: values
        for key, values in alias_targets.items()
        if len(values) > 1
    }

    if not result_collisions:
        print("Aucune collision.")
    else:
        for result_key, canonical_keys in (
            result_collisions.items()
        ):
            print("Résultat :", result_key)

            for canonical_key in sorted(
                canonical_keys
            ):
                print(
                    "  ->",
                    canonical_key,
                )

    print()
    print("=" * 125)
    print("FUSIONS : PLUSIEURS CLÉS RÉSULTATS VERS UNE IDENTITÉ EMS")
    print("=" * 125)

    canonical_collisions = {
        key: values
        for key, values in canonical_sources.items()
        if len(values) > 1
    }

    if not canonical_collisions:
        print("Aucune fusion multiple.")
    else:
        for canonical_key, result_keys in (
            canonical_collisions.items()
        ):
            print("Identité EMS :", canonical_key)

            for result_key in sorted(
                result_keys
            ):
                print(
                    "  <-",
                    result_key,
                )

    print()
    print("=" * 125)
    print("CLÉS ABSENTES DES FICHIERS")
    print("=" * 125)

    for row in audit_rows:
        problems = []

        if row["EmsFieldsTotal"] == 0:
            problems.append(
                "clé EMS absente"
            )

        if row["ResultFieldsTotal"] == 0:
            problems.append(
                "clé résultats absente"
            )

        if problems:
            print(
                f"{row['EmsName']} ↔ "
                f"{row['ResultName']} : "
                f"{', '.join(problems)}"
            )


if __name__ == "__main__":
    main()