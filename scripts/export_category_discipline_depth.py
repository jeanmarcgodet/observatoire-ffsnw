"""Mesure la profondeur des champs categorie-discipline."""

import csv
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


CATEGORY_FILE = Path(
    "data/exports/participation_categories_2017_2026.csv"
)

IDENTITY_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

OUTPUT_FILE = Path(
    "data/exports/profondeur_epreuves_categories_2017_2026.csv"
)

DISCIPLINES = (
    "slalom",
    "tricks",
    "jump",
)

DISCIPLINE_LABELS = {
    "slalom": "Slalom",
    "tricks": "Figures",
    "jump": "Saut",
}


def normalize_category(value):
    category = (value or "").strip().upper()

    legacy = {
        "-10": "U10",
        "-12": "U12",
        "-17": "U17",
    }

    return legacy.get(category, category)


def category_sort_key(category):
    if category.startswith("U"):
        digits = "".join(
            character
            for character in category
            if character.isdigit()
        )

        return (
            1,
            int(digits) if digits else 999,
        )

    if category == "OPEN":
        return (2, 0)

    if category.endswith("+"):
        digits = "".join(
            character
            for character in category
            if character.isdigit()
        )

        return (
            3,
            int(digits) if digits else 999,
        )

    return (4, 999)


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


aliases = load_aliases()


with CATEGORY_FILE.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    category_rows = list(
        csv.DictReader(
            handle,
            delimiter=";",
        )
    )


active_category_years = {
    (
        int(row["annee"]),
        normalize_category(row["categorie"]),
    )
    for row in category_rows
}


with sqlite3.connect(DATABASE_FILE) as database:
    result_rows = database.execute(
        """
        SELECT
            c.iwwf_id,
            re.rider_id,
            LOWER(TRIM(re.discipline)),
            rc.categorie,
            COALESCE(r.sexe, '')
        FROM results re
        JOIN competitions c
          ON c.id = re.competition_id
        JOIN result_classifications rc
          ON rc.result_id = re.id
        JOIN riders r
          ON r.id = re.rider_id
        WHERE CAST(
            SUBSTR(c.iwwf_id, 1, 2)
            AS INTEGER
        ) BETWEEN 17 AND 26
        """
    ).fetchall()


participants = defaultdict(set)
sexes = {}


for (
    competition_code,
    rider_id,
    discipline,
    category,
    sex,
) in result_rows:
    if discipline not in DISCIPLINES:
        continue

    year = 2000 + int(
        competition_code[:2]
    )

    category = normalize_category(category)

    rider_id = canonical_id(
        rider_id,
        aliases,
    )

    participants[
        (year, category, discipline)
    ].add(rider_id)

    sexes[rider_id] = sex.strip().upper()


export_rows = []


for year, category in sorted(
    active_category_years,
    key=lambda item: (
        item[0],
        category_sort_key(item[1]),
    ),
):
    for discipline in DISCIPLINES:
        rider_ids = participants.get(
            (year, category, discipline),
            set(),
        )

        women = sum(
            sexes.get(rider_id) == "F"
            for rider_id in rider_ids
        )

        men = sum(
            sexes.get(rider_id) == "M"
            for rider_id in rider_ids
        )

        participant_count = len(rider_ids)

        export_rows.append(
            {
                "annee": year,
                "categorie": category,
                "discipline": discipline,
                "participants": participant_count,
                "femmes": women,
                "hommes": men,
                "poids_une_personne_pct": (
                    f"{100 / participant_count:.1f}"
                    if participant_count
                    else ""
                ),
            }
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


print("=" * 88)
print("PROFONDEUR DES EPREUVES PAR CATEGORIE EN 2026")
print("=" * 88)

print(
    f"{'Categorie':<12}"
    f"{'Slalom':>10}"
    f"{'Figures':>10}"
    f"{'Saut':>10}"
)

categories_2026 = sorted(
    {
        category
        for year, category
        in active_category_years
        if year == 2026
    },
    key=category_sort_key,
)

lookup = {
    (
        row["annee"],
        row["categorie"],
        row["discipline"],
    ): row["participants"]
    for row in export_rows
}


for category in categories_2026:
    print(
        f"{category:<12}"
        f"{lookup[(2026, category, 'slalom')]:>10}"
        f"{lookup[(2026, category, 'tricks')]:>10}"
        f"{lookup[(2026, category, 'jump')]:>10}"
    )


values = [
    row["participants"]
    for row in export_rows
]

empty = sum(
    value == 0
    for value in values
)

one_to_three = sum(
    1 <= value <= 3
    for value in values
)

four_to_nine = sum(
    4 <= value <= 9
    for value in values
)

ten_to_nineteen = sum(
    10 <= value <= 19
    for value in values
)

twenty_or_more = sum(
    value >= 20
    for value in values
)


print()
print("=" * 88)
print("DISTRIBUTION DES CHAMPS CATEGORIE-DISCIPLINE 2017-2026")
print("=" * 88)
print("Champs potentiels       :", len(values))
print("Aucun participant      :", empty)
print("De 1 a 3 participants  :", one_to_three)
print("De 4 a 9 participants  :", four_to_nine)
print("De 10 a 19 participants:", ten_to_nineteen)
print("20 participants ou plus:", twenty_or_more)


print()
print("=" * 88)
print("SYNTHESE PAR DISCIPLINE")
print("=" * 88)

for discipline in DISCIPLINES:
    discipline_values = [
        row["participants"]
        for row in export_rows
        if row["discipline"] == discipline
    ]

    nonzero_values = [
        value
        for value in discipline_values
        if value > 0
    ]

    print(
        f"{DISCIPLINE_LABELS[discipline]:<10} "
        f"champs={len(discipline_values):>3} "
        f"vides={sum(value == 0 for value in discipline_values):>3} "
        f"mediane_tous={statistics.median(discipline_values):>4.1f} "
        f"mediane_non_vides="
        f"{statistics.median(nonzero_values):>4.1f} "
        f"maximum={max(discipline_values):>2}"
    )


print()
print("Fichier genere :", OUTPUT_FILE)
