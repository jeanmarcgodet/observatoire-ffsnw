"""Analyse la persistance individuelle aux Championnats de France."""

import csv
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


IDENTITY_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

OUTPUT_FILE = Path(
    "data/exports/persistance_participation_2017_2026.csv"
)

CODES = (
    "17FRA002", "17FRA005",
    "18FRA001", "18FRA010", "18FRA030",
    "19FRA001", "19FRA002", "19FRA03",
    "20FRA029", "20FRA030", "20FRA031",
    "21FRA044", "21FRA045", "21FRA046",
    "22FRA029", "22FRA030", "22FRA031",
    "23FRA017", "23FRA018", "23FRA023",
    "24FRA026", "24FRA027", "24FRA034",
    "25FRA016", "25FRA018", "25FRA206",
    "26FRA020", "26FRA021", "26FRA041",
)


def load_aliases():
    aliases = {}

    with IDENTITY_FILE.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(
            handle,
            delimiter=";",
        ):
            aliases[
                int(row["alias_rider_id"])
            ] = int(row["canonical_rider_id"])

    return aliases


def canonical_id(rider_id, aliases):
    current = rider_id
    visited = set()

    while current in aliases:
        if current in visited:
            raise RuntimeError(
                f"Cycle d'identite pour {rider_id}"
            )

        visited.add(current)
        current = aliases[current]

    return current


def normalize_category(value):
    category = (value or "").strip().upper()

    legacy = {
        "-10": "U10",
        "-12": "U12",
        "-17": "U17",
    }

    return legacy.get(category, category)


def longest_consecutive_streak(years):
    ordered = sorted(years)

    if not ordered:
        return 0

    longest = 1
    current = 1

    for previous, year in zip(
        ordered,
        ordered[1:],
    ):
        if year == previous + 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


aliases = load_aliases()
placeholders = ",".join("?" for _ in CODES)


with sqlite3.connect(DATABASE_FILE) as database:
    entry_rows = database.execute(
        f"""
        SELECT
            c.iwwf_id,
            e.rider_id,
            e.categorie
        FROM entries e
        JOIN competitions c
          ON c.id = e.competition_id
        WHERE c.iwwf_id IN ({placeholders})
        """,
        CODES,
    ).fetchall()

    rider_rows = database.execute(
        """
        SELECT
            id,
            COALESCE(prenom, ''),
            COALESCE(nom, ''),
            COALESCE(sexe, '')
        FROM riders
        """
    ).fetchall()


riders = {
    rider_id: {
        "prenom": first_name.strip(),
        "nom": last_name.strip(),
        "sexe": sex.strip().upper(),
    }
    for rider_id, first_name, last_name, sex
    in rider_rows
}


years_by_rider = defaultdict(set)
competitions_by_rider = defaultdict(set)
categories_by_rider = defaultdict(set)


for competition_code, rider_id, category in entry_rows:
    rider_id = canonical_id(
        rider_id,
        aliases,
    )

    year = 2000 + int(
        competition_code[:2]
    )

    years_by_rider[rider_id].add(year)

    competitions_by_rider[rider_id].add(
        competition_code
    )

    categories_by_rider[rider_id].add(
        normalize_category(category)
    )


export_rows = []


for rider_id, years in years_by_rider.items():
    ordered_years = sorted(years)

    rider = riders.get(
        rider_id,
        {
            "prenom": "",
            "nom": "",
            "sexe": "",
        },
    )

    export_rows.append(
        {
            "rider_id_canonique": rider_id,
            "prenom": rider["prenom"],
            "nom": rider["nom"],
            "sexe": rider["sexe"],
            "premiere_annee": ordered_years[0],
            "derniere_annee": ordered_years[-1],
            "nombre_annees": len(ordered_years),
            "plus_longue_sequence_consecutive": (
                longest_consecutive_streak(years)
            ),
            "nombre_competitions": len(
                competitions_by_rider[rider_id]
            ),
            "annees": ",".join(
                str(year)
                for year in ordered_years
            ),
            "categories": ",".join(
                sorted(
                    categories_by_rider[rider_id]
                )
            ),
        }
    )


export_rows.sort(
    key=lambda row: (
        -row["nombre_annees"],
        row["nom"],
        row["prenom"],
    )
)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with OUTPUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=list(export_rows[0]),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(export_rows)


total = len(export_rows)

year_counts = [
    row["nombre_annees"]
    for row in export_rows
]

one_year = sum(
    count == 1
    for count in year_counts
)

two_to_three = sum(
    2 <= count <= 3
    for count in year_counts
)

four_to_six = sum(
    4 <= count <= 6
    for count in year_counts
)

seven_to_ten = sum(
    7 <= count <= 10
    for count in year_counts
)

five_or_more = sum(
    count >= 5
    for count in year_counts
)

all_ten_years = sum(
    count == 10
    for count in year_counts
)


cohort_2017 = [
    row
    for row in export_rows
    if 2017 in {
        int(year)
        for year in row["annees"].split(",")
    }
]

cohort_2017_present_2026 = [
    row
    for row in cohort_2017
    if 2026 in {
        int(year)
        for year in row["annees"].split(",")
    }
]


print("=" * 92)
print("PERSISTANCE INDIVIDUELLE 2017-2026")
print("=" * 92)
print("Participants uniques observes :", total)
print(
    "Mediane d'annees observees     :",
    f"{statistics.median(year_counts):.1f}",
)
print(
    "Moyenne d'annees observees     :",
    f"{statistics.mean(year_counts):.1f}",
)
print(
    "Poids d'une personne           :",
    f"{100 / total:.1f} point",
)

print()
print("REPARTITION PAR NOMBRE D'ANNEES")
print(
    "Une seule annee                :",
    f"{one_year}/{total}",
    f"({100 * one_year / total:.1f} %)",
)
print(
    "Deux a trois annees            :",
    f"{two_to_three}/{total}",
    f"({100 * two_to_three / total:.1f} %)",
)
print(
    "Quatre a six annees            :",
    f"{four_to_six}/{total}",
    f"({100 * four_to_six / total:.1f} %)",
)
print(
    "Sept a dix annees              :",
    f"{seven_to_ten}/{total}",
    f"({100 * seven_to_ten / total:.1f} %)",
)
print(
    "Au moins cinq annees           :",
    f"{five_or_more}/{total}",
    f"({100 * five_or_more / total:.1f} %)",
)
print(
    "Present les dix annees         :",
    f"{all_ten_years}/{total}",
    f"({100 * all_ten_years / total:.1f} %)",
)

print()
print("COHORTE OBSERVEE EN 2017")
print("Participants en 2017           :", len(cohort_2017))
print(
    "Egalement presents en 2026     :",
    f"{len(cohort_2017_present_2026)}/{len(cohort_2017)}",
    (
        f"({100 * len(cohort_2017_present_2026) / len(cohort_2017):.1f} %)"
        if cohort_2017
        else "-"
    ),
)
print(
    "Attention : presence en 2017 et 2026 "
    "ne signifie pas participation continue."
)

print()
print("PERSISTANCE PAR SEXE")

for sex, label in (
    ("F", "Femmes"),
    ("M", "Hommes"),
):
    group = [
        row
        for row in export_rows
        if row["sexe"] == sex
    ]

    group_one_year = sum(
        row["nombre_annees"] == 1
        for row in group
    )

    group_five_or_more = sum(
        row["nombre_annees"] >= 5
        for row in group
    )

    group_all_ten = sum(
        row["nombre_annees"] == 10
        for row in group
    )

    print()
    print(f"{label} : {len(group)} personnes")

    if group:
        print(
            "  Une seule annee      :",
            f"{group_one_year}/{len(group)}",
            f"({100 * group_one_year / len(group):.1f} %)",
        )
        print(
            "  Au moins cinq annees :",
            f"{group_five_or_more}/{len(group)}",
            f"({100 * group_five_or_more / len(group):.1f} %)",
        )
        print(
            "  Les dix annees       :",
            f"{group_all_ten}/{len(group)}",
        )
        print(
            "  Poids d'une personne :",
            f"{100 / len(group):.1f} points",
        )

print()
print("Fichier genere :", OUTPUT_FILE)
