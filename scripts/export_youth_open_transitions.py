"""Analyse les trajectoires des categories jeunes vers l'Open."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


COMPETITION_CODES = (
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

IDENTITY_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

OUTPUT_FILE = Path(
    "data/exports/trajectoires_jeunes_open_2017_2023.csv"
)


def load_alias_map() -> dict[int, int]:
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


def canonical_id(
    rider_id: int,
    aliases: dict[int, int],
) -> int:
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


def normalized_category(value: str) -> str:
    return (value or "").strip().upper()


def category_sort_key(value: str):
    digits = "".join(
        character
        for character in value
        if character.isdigit()
    )

    return (
        int(digits) if digits else 999,
        value,
    )


aliases = load_alias_map()

placeholders = ",".join(
    "?" for _ in COMPETITION_CODES
)

with sqlite3.connect(DATABASE_FILE) as database:
    rows = database.execute(
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
        COMPETITION_CODES,
    ).fetchall()

    rider_details = {
        row[0]: {
            "prenom": row[1] or "",
            "nom": row[2] or "",
            "sexe": (row[3] or "").strip().upper(),
        }
        for row in database.execute(
            """
            SELECT
                id,
                prenom,
                nom,
                sexe
            FROM riders
            """
        )
    }


observations = defaultdict(set)

for code, rider_id, category in rows:
    year = 2000 + int(code[:2])

    rider_id = canonical_id(
        rider_id,
        aliases,
    )

    observations[rider_id].add(
        (
            year,
            normalized_category(category),
        )
    )


trajectory_rows = []

for rider_id, rider_observations in observations.items():
    youth_observations = {
        (year, category)
        for year, category in rider_observations
        if category.startswith("U")
    }

    if not youth_observations:
        continue

    last_youth_year = max(
        year
        for year, category in youth_observations
    )

    # Trois années complètes de recul.
    if last_youth_year > 2023:
        continue

    last_categories = sorted(
        {
            category
            for year, category in youth_observations
            if year == last_youth_year
        },
        key=category_sort_key,
    )

    last_category = " / ".join(
        last_categories
    )

    open_years = sorted(
        {
            year
            for year, category in rider_observations
            if category == "OPEN"
            and last_youth_year
            <= year
            <= last_youth_year + 3
        }
    )

    future_observations = {
        (year, category)
        for year, category in rider_observations
        if last_youth_year
        < year
        <= last_youth_year + 3
    }

    if open_years:
        first_open_year = open_years[0]
        delay = first_open_year - last_youth_year
        outcome = "passage_open"
    elif future_observations:
        first_open_year = ""
        delay = ""
        outcome = "autre_continuite"
    else:
        first_open_year = ""
        delay = ""
        outcome = "disparition_observee"

    details = rider_details.get(
        rider_id,
        {
            "prenom": "",
            "nom": "",
            "sexe": "",
        },
    )

    trajectory_rows.append(
        {
            "rider_id_canonique": rider_id,
            "prenom": details["prenom"],
            "nom": details["nom"],
            "sexe": details["sexe"],
            "derniere_annee_jeune": (
                last_youth_year
            ),
            "derniere_categorie_jeune": (
                last_category
            ),
            "premiere_annee_open": (
                first_open_year
            ),
            "delai_vers_open": delay,
            "issue_sous_trois_ans": outcome,
        }
    )


trajectory_rows.sort(
    key=lambda row: (
        row["derniere_annee_jeune"],
        category_sort_key(
            row["derniere_categorie_jeune"]
        ),
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
        fieldnames=list(
            trajectory_rows[0]
        ),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(trajectory_rows)


print("=" * 96)
print("PASSAGES JEUNES VERS OPEN SELON LE DELAI")
print("=" * 96)

by_category = defaultdict(list)

for row in trajectory_rows:
    by_category[
        row["derniere_categorie_jeune"]
    ].append(row)

for category in sorted(
    by_category,
    key=category_sort_key,
):
    group = by_category[category]
    delays = Counter(
        row["delai_vers_open"]
        for row in group
        if row["issue_sous_trois_ans"]
        == "passage_open"
    )

    open_total = sum(delays.values())
    disappeared = sum(
        row["issue_sous_trois_ans"]
        == "disparition_observee"
        for row in group
    )

    print(
        f"{category:<12} "
        f"cohorte={len(group):>3} "
        f"meme_annee={delays[0]:>2} "
        f"a_1_an={delays[1]:>2} "
        f"a_2_ans={delays[2]:>2} "
        f"a_3_ans={delays[3]:>2} "
        f"total_Open={open_total:>2} "
        f"disparus={disappeared:>3}"
    )


u21_rows = [
    row
    for row in trajectory_rows
    if row["derniere_categorie_jeune"]
    == "U21"
]

u21_delays = Counter(
    row["delai_vers_open"]
    for row in u21_rows
    if row["issue_sous_trois_ans"]
    == "passage_open"
)

u21_open = sum(u21_delays.values())
u21_disappeared = sum(
    row["issue_sous_trois_ans"]
    == "disparition_observee"
    for row in u21_rows
)

print()
print("=" * 96)
print("FOCUS TRANSITION U21 VERS OPEN")
print("=" * 96)
print("Cohorte U21             :", len(u21_rows))
print("Passage la meme annee   :", u21_delays[0])
print("Passage a un an         :", u21_delays[1])
print("Passage a deux ans      :", u21_delays[2])
print("Passage a trois ans     :", u21_delays[3])
print("Passages totaux         :", u21_open)
print(
    "Taux de passage         :",
    (
        f"{100 * u21_open / len(u21_rows):.1f} %"
        if u21_rows
        else "-"
    ),
)
print(
    "Disparitions observees :",
    u21_disappeared,
)

print()
print("TRANSITION U21 VERS OPEN PAR SEXE")

for sex, label in (
    ("F", "Femmes"),
    ("M", "Hommes"),
):
    group = [
        row
        for row in u21_rows
        if row["sexe"] == sex
    ]

    transitions = sum(
        row["issue_sous_trois_ans"]
        == "passage_open"
        for row in group
    )

    rate = (
        100 * transitions / len(group)
        if group
        else 0
    )

    print(
        f"{label:<7}: "
        f"{transitions}/{len(group)} "
        f"({rate:.1f} %)"
    )

print()
print("Fichier genere :", OUTPUT_FILE)
