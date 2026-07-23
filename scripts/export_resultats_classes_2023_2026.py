"""Exporte les présences classées individuelles des Championnats de France."""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from observatoire.config import DATABASE_FILE


ROOT = Path(__file__).resolve().parents[1]

COUNTRY_OVERRIDES_FILE = (
    ROOT
    / "data/reference/"
    / "championship_country_overrides.csv"
)

CHAMPIONSHIPS = {
    "23FRA017": "RELEVES",
    "23FRA018": "U21_OPEN",
    "23FRA023": "SENIOR",
    "24FRA026": "RELEVES",
    "24FRA027": "U21_OPEN",
    "24FRA034": "SENIOR",
    "25FRA016": "RELEVES",
    "25FRA206": "U21_OPEN",
    "25FRA018": "SENIOR",
    "26FRA020": "RELEVES",
    "26FRA021": "U21_OPEN",
    "26FRA041": "SENIOR",
}

EVENT_MAP = {
    "slalom": "SLALOM",
    "tricks": "FIGURES",
    "jump": "SAUT",
    "overall": "COMBINE",
}

ALLOWED_POPULATIONS = {
    "RELEVES": {"RELEVES", "JUNIOR"},
    "U21_OPEN": {"U21", "OPEN"},
    "SENIOR": {"SENIOR"},
}


def normalize_spaces(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def normalize_name(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        normalize_spaces(value),
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)

    return normalize_spaces(value)


def normalize_category(value: str) -> str:
    value = normalize_spaces(value).upper()

    value = value.replace(" ", "")

    if value.startswith("-"):
        value = "U" + value[1:]

    return value


def population_group(category: str) -> str:
    if category in {
        "U8",
        "U10",
        "U12",
        "U14",
    }:
        return "RELEVES"

    if category == "U17":
        return "JUNIOR"

    if category == "U21":
        return "U21"

    if category in {"OPEN", "PRO"}:
        return "OPEN"

    if re.fullmatch(r"\d+\+", category):
        return "SENIOR"

    return "AUTRE"


def join_values(values: set[str]) -> str:
    return " | ".join(
        sorted(
            value
            for value in values
            if value
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



def load_country_overrides(
    path: Path,
) -> dict[tuple[str, int], str]:
    overrides: dict[
        tuple[str, int],
        str,
    ] = {}

    if not path.exists():
        return overrides

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter=";",
        )

        for row in reader:
            code = normalize_spaces(
                row.get("CompetitionCode", "")
            )

            rider_id_text = normalize_spaces(
                row.get("RiderId", "")
            )

            country = normalize_spaces(
                row.get("Country", "")
            ).upper()

            if (
                not code
                or not rider_id_text
                or not country
            ):
                continue

            overrides[
                (
                    code,
                    int(rider_id_text),
                )
            ] = country

    return overrides


def main() -> None:
    country_overrides = (
        load_country_overrides(
            COUNTRY_OVERRIDES_FILE
        )
    )

    codes = tuple(CHAMPIONSHIPS)
    placeholders = ",".join(
        "?"
        for _ in codes
    )

    with sqlite3.connect(DATABASE_FILE) as database:
        database.row_factory = sqlite3.Row

        raw_rows = database.execute(
            f"""
            SELECT
                c.iwwf_id AS competition_code,
                c.nom AS competition_name,

                r.id AS rider_id,
                r.iwwf_id AS rider_iwwf_id,
                r.ems_athlete_id,
                r.nom,
                r.prenom,
                r.sexe AS rider_sex,
                r.nation,
                r.annee_naissance,

                re.id AS result_id,
                re.discipline,
                re.tour,
                re.score,

                rc.classement,
                rc.categorie,
                rc.sexe AS classification_sex,
                rc.rang,
                rc.ligue,
                rc.fichier_source

            FROM results re

            JOIN competitions c
              ON c.id = re.competition_id

            JOIN riders r
              ON r.id = re.rider_id

            JOIN result_classifications rc
              ON rc.result_id = re.id

            WHERE c.iwwf_id IN ({placeholders})

            ORDER BY
                c.iwwf_id,
                r.id,
                re.discipline,
                rc.categorie,
                re.tour,
                rc.rang
            """,
            codes,
        ).fetchall()

    grouped: dict[
        tuple[Any, ...],
        dict[str, Any],
    ] = {}

    anomalies: list[dict[str, Any]] = []

    for row in raw_rows:
        code = normalize_spaces(
            row["competition_code"]
        )

        block = CHAMPIONSHIPS[code]

        category = normalize_category(
            row["categorie"]
        )

        population = population_group(
            category
        )

        discipline_raw = normalize_spaces(
            row["discipline"]
        ).lower()

        event = EVENT_MAP.get(
            discipline_raw,
            "",
        )

        sex = normalize_spaces(
            row["classification_sex"]
            or row["rider_sex"]
        ).upper()

        database_nation = normalize_spaces(
            row["nation"]
        ).upper()

        nation = country_overrides.get(
            (
                code,
                int(row["rider_id"]),
            ),
            database_nation,
        )

        name = normalize_spaces(
            f"{row['nom']} {row['prenom']}"
        )

        normalized_name = normalize_name(name)

        yob = row["annee_naissance"] or ""

        athlete_key = (
            f"{nation}|{yob}|{normalized_name}"
        )

        title_eligible = (
            population
            in ALLOWED_POPULATIONS[block]
        )

        if not event:
            anomalies.append(
                {
                    "CompetitionCode": code,
                    "RiderId": row["rider_id"],
                    "Name": name,
                    "Category": category,
                    "Sex": sex,
                    "DisciplineRaw": discipline_raw,
                    "AnomalyType": "UNKNOWN_EVENT",
                }
            )
            continue

        if population == "AUTRE":
            anomalies.append(
                {
                    "CompetitionCode": code,
                    "RiderId": row["rider_id"],
                    "Name": name,
                    "Category": category,
                    "Sex": sex,
                    "DisciplineRaw": discipline_raw,
                    "AnomalyType": "UNKNOWN_CATEGORY",
                }
            )

        key = (
            code,
            row["rider_id"],
            category,
            sex,
            event,
        )

        if key not in grouped:
            grouped[key] = {
                "Year": 2000 + int(code[:2]),
                "CompetitionCode": code,
                "CompetitionName": normalize_spaces(
                    row["competition_name"]
                ),
                "ChampionshipBlock": block,
                "TitleEligible": int(
                    title_eligible
                ),
                "PopulationGroup": population,
                "Category": category,
                "Sex": sex,
                "Event": event,
                "RiderId": row["rider_id"],
                "RiderIwwfId": normalize_spaces(
                    row["rider_iwwf_id"]
                ),
                "EmsAthleteId": normalize_spaces(
                    row["ems_athlete_id"]
                ),
                "AthleteKey": athlete_key,
                "Name": name,
                "NormalizedName": normalized_name,
                "Country": nation,
                "IsFrench": int(
                    nation == "FRA"
                ),
                "YOB": yob,
                "ResultRows": 0,
                "_result_ids": set(),
                "_tours": set(),
                "_scores": set(),
                "_classifications": set(),
                "_ranks": set(),
                "_sources": set(),
            }

        item = grouped[key]

        item["ResultRows"] += 1

        item["_result_ids"].add(
            str(row["result_id"] or "")
        )

        item["_tours"].add(
            normalize_spaces(row["tour"])
        )

        item["_scores"].add(
            normalize_spaces(row["score"])
        )

        item["_classifications"].add(
            normalize_spaces(
                row["classement"]
            )
        )

        if row["rang"] is not None:
            item["_ranks"].add(
                str(row["rang"])
            )

        item["_sources"].add(
            normalize_spaces(
                row["fichier_source"]
            )
        )

    output_rows: list[dict[str, Any]] = []

    for item in grouped.values():
        output_rows.append(
            {
                key: value
                for key, value in item.items()
                if not key.startswith("_")
            }
            | {
                "ResultIds": join_values(
                    item["_result_ids"]
                ),
                "Tours": join_values(
                    item["_tours"]
                ),
                "Scores": join_values(
                    item["_scores"]
                ),
                "Classifications": join_values(
                    item["_classifications"]
                ),
                "Ranks": join_values(
                    item["_ranks"]
                ),
                "SourceFiles": join_values(
                    item["_sources"]
                ),
            }
        )

    output_rows.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["ChampionshipBlock"]),
            str(row["Category"]),
            str(row["Sex"]),
            str(row["Event"]),
            str(row["NormalizedName"]),
        )
    )

    field_groups: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in output_rows:
        key = (
            row["Year"],
            row["CompetitionCode"],
            row["ChampionshipBlock"],
            row["TitleEligible"],
            row["PopulationGroup"],
            row["Category"],
            row["Sex"],
            row["Event"],
        )

        field_groups[key].append(row)

    field_rows: list[dict[str, Any]] = []

    for key, rows in field_groups.items():
        (
            year,
            code,
            block,
            title_eligible,
            population,
            category,
            sex,
            event,
        ) = key

        all_riders = {
            row["RiderId"]
            for row in rows
        }

        french_riders = {
            row["RiderId"]
            for row in rows
            if int(row["IsFrench"]) == 1
        }

        field_rows.append(
            {
                "Year": year,
                "CompetitionCode": code,
                "CompetitionName": rows[0][
                    "CompetitionName"
                ],
                "ChampionshipBlock": block,
                "TitleEligible": title_eligible,
                "PopulationGroup": population,
                "Category": category,
                "Sex": sex,
                "Event": event,
                "ClassifiedAll": len(
                    all_riders
                ),
                "ClassifiedFrench": len(
                    french_riders
                ),
                "ClassifiedForeign": (
                    len(all_riders)
                    - len(french_riders)
                ),
            }
        )

    field_rows.sort(
        key=lambda row: (
            int(row["Year"]),
            str(row["ChampionshipBlock"]),
            str(row["Category"]),
            str(row["Sex"]),
            str(row["Event"]),
        )
    )

    output_path = (
        ROOT
        / "data/processed/"
        / "resultats_classes_individuels_2023_2026.csv"
    )

    fields_path = (
        ROOT
        / "data/processed/"
        / "resultats_classes_champs_2023_2026.csv"
    )

    anomalies_path = (
        ROOT
        / "data/processed/"
        / "resultats_classes_anomalies_2023_2026.csv"
    )

    write_csv(
        output_path,
        output_rows,
    )

    write_csv(
        fields_path,
        field_rows,
    )

    write_csv(
        anomalies_path,
        anomalies,
        fieldnames=[
            "CompetitionCode",
            "RiderId",
            "Name",
            "Category",
            "Sex",
            "DisciplineRaw",
            "AnomalyType",
        ],
    )

    print("=" * 105)
    print("RÉSULTATS CLASSÉS DÉDUPLIQUÉS — 2023 À 2026")
    print("=" * 105)

    print(
        "Lignes brutes de classification :",
        len(raw_rows),
    )

    print(
        "Présences classées distinctes   :",
        len(output_rows),
    )

    print(
        "Champs classés distincts         :",
        len(field_rows),
    )

    print(
        "Anomalies                        :",
        len(anomalies),
    )

    print()
    print(
        f"{'Année':<7}"
        f"{'Bloc':<12}"
        f"{'Sportifs FRA':>14}"
        f"{'Particip. FRA':>15}"
        f"{'Champs':>10}"
    )
    print("-" * 58)

    for year in range(2023, 2027):
        for block in (
            "RELEVES",
            "U21_OPEN",
            "SENIOR",
        ):
            rows = [
                row
                for row in output_rows
                if int(row["Year"]) == year
                and row["ChampionshipBlock"] == block
                and int(row["TitleEligible"]) == 1
                and int(row["IsFrench"]) == 1
            ]

            athletes = {
                row["RiderId"]
                for row in rows
            }

            fields = {
                (
                    row["Category"],
                    row["Sex"],
                    row["Event"],
                )
                for row in rows
            }

            print(
                f"{year:<7}"
                f"{block:<12}"
                f"{len(athletes):>14}"
                f"{len(rows):>15}"
                f"{len(fields):>10}"
            )

    print()
    print("CSV individuel :", output_path)
    print("CSV champs     :", fields_path)
    print("CSV anomalies  :", anomalies_path)


if __name__ == "__main__":
    main()