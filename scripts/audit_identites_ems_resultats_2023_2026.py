"""Produit les candidats de rapprochement entre identités EMS et résultats."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
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

OUTPUT_CANDIDATES = (
    ROOT
    / "data/processed/"
    / "candidats_identites_ems_resultats_2023_2026.csv"
)

OUTPUT_RESIDUALS = (
    ROOT
    / "data/processed/"
    / "ecarts_identites_residuels_2023_2026.csv"
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


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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


def yob_from_key(value: Any) -> str:
    parts = str(value or "").split("|")

    if len(parts) >= 2:
        return parts[1].strip()

    return ""


def name_score(
    first_name: str,
    second_name: str,
) -> float:
    first = normalize_text(first_name)
    second = normalize_text(second_name)

    if not first or not second:
        return 0.0

    if first == second:
        return 100.0

    sequence_score = (
        100
        * SequenceMatcher(
            None,
            first,
            second,
        ).ratio()
    )

    first_tokens = first.split()
    second_tokens = second.split()

    first_set = set(first_tokens)
    second_set = set(second_tokens)

    common = first_set & second_set

    containment = (
        len(common)
        / min(
            len(first_set),
            len(second_set),
        )
        if first_set and second_set
        else 0
    )

    containment_score = 100 * containment

    combined_score = (
        0.70 * containment_score
        + 0.30 * sequence_score
    )

    score = max(
        sequence_score,
        combined_score,
    )

    if (
        first_tokens
        and second_tokens
        and first_tokens[0] == second_tokens[0]
    ):
        score += 3

    return round(
        min(score, 100),
        1,
    )


def confidence_level(
    ems_name: str,
    result_name: str,
    ems_yob: str,
    result_yob: str,
    score: float,
) -> str:
    normalized_ems = normalize_text(
        ems_name
    )

    normalized_result = normalize_text(
        result_name
    )

    same_yob = (
        ems_yob
        and result_yob
        and ems_yob == result_yob
    )

    yob_missing = (
        not ems_yob
        or not result_yob
    )

    if normalized_ems == normalized_result:
        return "AUTO_EXACT_NAME"

    if score >= 92 and (
        same_yob
        or yob_missing
    ):
        return "AUTO_STRONG"

    if score >= 82:
        return "REVIEW_HIGH"

    if score >= 70:
        return "REVIEW_MEDIUM"

    return "LOW"


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
            str(row["AthleteKey"])
        ] = row

    for row in result_rows:
        result_fields[field_key(row)][
            str(row["AthleteKey"])
        ] = row

    pair_occurrences: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    residual_rows: list[dict[str, Any]] = []

    exact_matches = 0
    proposed_matches = 0

    all_fields = sorted(
        set(ems_fields)
        | set(result_fields)
    )

    for field in all_fields:
        ems_people = ems_fields.get(
            field,
            {},
        )

        result_people = result_fields.get(
            field,
            {},
        )

        exact_keys = (
            set(ems_people)
            & set(result_people)
        )

        exact_matches += len(exact_keys)

        unmatched_ems = {
            key: value
            for key, value in ems_people.items()
            if key not in exact_keys
        }

        unmatched_results = {
            key: value
            for key, value in result_people.items()
            if key not in exact_keys
        }

        candidate_scores: list[
            tuple[
                float,
                str,
                str,
                dict[str, str],
                dict[str, str],
            ]
        ] = []

        for ems_key, ems_row in unmatched_ems.items():
            for (
                result_key,
                result_row,
            ) in unmatched_results.items():
                score = name_score(
                    ems_row.get("Name", ""),
                    result_row.get("Name", ""),
                )

                candidate_scores.append(
                    (
                        score,
                        ems_key,
                        result_key,
                        ems_row,
                        result_row,
                    )
                )

        candidate_scores.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        used_ems: set[str] = set()
        used_results: set[str] = set()

        for (
            score,
            ems_key,
            result_key,
            ems_row,
            result_row,
        ) in candidate_scores:
            if score < 70:
                continue

            if (
                ems_key in used_ems
                or result_key in used_results
            ):
                continue

            ems_yob = yob_from_key(
                ems_key
            )

            result_yob = str(
                result_row.get("YOB", "")
            ).strip()

            confidence = confidence_level(
                ems_row.get("Name", ""),
                result_row.get("Name", ""),
                ems_yob,
                result_yob,
                score,
            )

            if confidence == "LOW":
                continue

            used_ems.add(ems_key)
            used_results.add(result_key)

            proposed_matches += 1

            pair_key = (
                normalize_text(
                    ems_row.get("Name", "")
                ),
                normalize_text(
                    result_row.get("Name", "")
                ),
                ems_yob,
                result_yob,
            )

            if pair_key not in pair_occurrences:
                pair_occurrences[pair_key] = {
                    "EmsName": ems_row.get(
                        "Name",
                        "",
                    ),
                    "ResultName": result_row.get(
                        "Name",
                        "",
                    ),
                    "EmsNormalizedName": pair_key[0],
                    "ResultNormalizedName": pair_key[1],
                    "EmsYOB": ems_yob,
                    "ResultYOB": result_yob,
                    "NameScore": score,
                    "Confidence": confidence,
                    "Occurrences": 0,
                    "_years": set(),
                    "_competitions": set(),
                    "_fields": set(),
                }

            item = pair_occurrences[pair_key]

            item["Occurrences"] += 1
            item["NameScore"] = max(
                float(item["NameScore"]),
                score,
            )

            item["_years"].add(
                field[0]
            )

            item["_competitions"].add(
                field[1]
            )

            item["_fields"].add(
                "|".join(
                    (
                        field[4],
                        field[5],
                        field[6],
                    )
                )
            )

        for ems_key, ems_row in unmatched_ems.items():
            if ems_key in used_ems:
                continue

            residual_rows.append(
                {
                    "Year": field[0],
                    "CompetitionCode": field[1],
                    "ChampionshipBlock": field[2],
                    "PopulationGroup": field[3],
                    "Category": field[4],
                    "Sex": field[5],
                    "Event": field[6],
                    "Status": "EMS_ONLY",
                    "AthleteKey": ems_key,
                    "Name": ems_row.get(
                        "Name",
                        "",
                    ),
                    "YOB": yob_from_key(
                        ems_key
                    ),
                }
            )

        for (
            result_key,
            result_row,
        ) in unmatched_results.items():
            if result_key in used_results:
                continue

            residual_rows.append(
                {
                    "Year": field[0],
                    "CompetitionCode": field[1],
                    "ChampionshipBlock": field[2],
                    "PopulationGroup": field[3],
                    "Category": field[4],
                    "Sex": field[5],
                    "Event": field[6],
                    "Status": "RESULTS_ONLY",
                    "AthleteKey": result_key,
                    "Name": result_row.get(
                        "Name",
                        "",
                    ),
                    "YOB": result_row.get(
                        "YOB",
                        "",
                    ),
                }
            )

    candidate_rows: list[dict[str, Any]] = []

    for item in pair_occurrences.values():
        candidate_rows.append(
            {
                key: value
                for key, value in item.items()
                if not key.startswith("_")
            }
            | {
                "Years": " | ".join(
                    sorted(item["_years"])
                ),
                "CompetitionCodes": " | ".join(
                    sorted(item["_competitions"])
                ),
                "Fields": " | ".join(
                    sorted(item["_fields"])
                ),
            }
        )

    confidence_order = {
        "AUTO_EXACT_NAME": 0,
        "AUTO_STRONG": 1,
        "REVIEW_HIGH": 2,
        "REVIEW_MEDIUM": 3,
    }

    candidate_rows.sort(
        key=lambda row: (
            confidence_order.get(
                str(row["Confidence"]),
                9,
            ),
            -int(row["Occurrences"]),
            -float(row["NameScore"]),
            str(row["EmsName"]),
        )
    )

    residual_rows.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["CompetitionCode"]),
            str(row["Category"]),
            str(row["Sex"]),
            str(row["Event"]),
            str(row["Status"]),
            str(row["Name"]),
        )
    )

    write_csv(
        OUTPUT_CANDIDATES,
        candidate_rows,
        fieldnames=[
            "EmsName",
            "ResultName",
            "EmsNormalizedName",
            "ResultNormalizedName",
            "EmsYOB",
            "ResultYOB",
            "NameScore",
            "Confidence",
            "Occurrences",
            "Years",
            "CompetitionCodes",
            "Fields",
        ],
    )

    write_csv(
        OUTPUT_RESIDUALS,
        residual_rows,
        fieldnames=[
            "Year",
            "CompetitionCode",
            "ChampionshipBlock",
            "PopulationGroup",
            "Category",
            "Sex",
            "Event",
            "Status",
            "AthleteKey",
            "Name",
            "YOB",
        ],
    )

    print("=" * 115)
    print(
        "AUDIT DES IDENTITÉS EMS / RÉSULTATS"
    )
    print("=" * 115)

    print(
        "Correspondances exactes initiales :",
        exact_matches,
    )

    print(
        "Rapprochements proposés          :",
        proposed_matches,
    )

    print(
        "Paires nominatives distinctes    :",
        len(candidate_rows),
    )

    print(
        "Écarts résiduels                 :",
        len(residual_rows),
    )

    print()
    print("CANDIDATS PAR NIVEAU")

    for confidence in (
        "AUTO_EXACT_NAME",
        "AUTO_STRONG",
        "REVIEW_HIGH",
        "REVIEW_MEDIUM",
    ):
        rows = [
            row
            for row in candidate_rows
            if row["Confidence"] == confidence
        ]

        print(
            f"{confidence:<20}: "
            f"{len(rows):>3} paires, "
            f"{sum(int(row['Occurrences']) for row in rows):>3} occurrences"
        )

    print()
    print(
        f"{'Niveau':<18}"
        f"{'Score':>7}  "
        f"{'Occ.':>5}  "
        f"{'EMS':<34}"
        f"{'Résultats'}"
    )

    print("-" * 115)

    for row in candidate_rows[:60]:
        print(
            f"{row['Confidence']:<18}"
            f"{float(row['NameScore']):>7.1f}  "
            f"{int(row['Occurrences']):>5}  "
            f"{str(row['EmsName']):<34}"
            f"{row['ResultName']}"
        )

    print()
    print("Candidats :", OUTPUT_CANDIDATES)
    print("Résiduels :", OUTPUT_RESIDUALS)


if __name__ == "__main__":
    main()