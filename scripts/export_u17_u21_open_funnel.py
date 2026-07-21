"""Construit l'entonnoir individuel U17 vers U21 vers Open."""

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


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

IDENTITY_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

OUTPUT_FILE = Path(
    "data/exports/entonnoir_u17_u21_open_2017_2020.csv"
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


def normalize_category(category):
    value = (category or "").strip().upper()

    legacy = {
        "-10": "U10",
        "-12": "U12",
        "-17": "U17",
    }

    return legacy.get(value, value)


aliases = load_aliases()
placeholders = ",".join("?" for _ in CODES)

with sqlite3.connect(DATABASE_FILE) as database:
    entries = database.execute(
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

    riders = {
        rider_id: {
            "prenom": first_name or "",
            "nom": last_name or "",
            "sexe": (sex or "").strip().upper(),
        }
        for rider_id, first_name, last_name, sex
        in database.execute(
            """
            SELECT id, prenom, nom, sexe
            FROM riders
            """
        )
    }


observations = defaultdict(set)

for code, rider_id, category in entries:
    year = 2000 + int(code[:2])

    rider_id = canonical_id(
        rider_id,
        aliases,
    )

    observations[rider_id].add(
        (
            year,
            normalize_category(category),
        )
    )


rows = []

for rider_id, rider_observations in observations.items():
    u17_years = {
        year
        for year, category in rider_observations
        if category == "U17"
    }

    if not u17_years:
        continue

    last_u17_year = max(u17_years)

    # Six années de recul disponibles jusqu'en 2026.
    if not 2017 <= last_u17_year <= 2020:
        continue

    u21_years = sorted(
        {
            year
            for year, category in rider_observations
            if category == "U21"
            and last_u17_year
            <= year
            <= last_u17_year + 3
        }
    )

    if u21_years:
        first_u21_year = u21_years[0]

        open_years = sorted(
            {
                year
                for year, category in rider_observations
                if category == "OPEN"
                and first_u21_year
                <= year
                <= first_u21_year + 3
            }
        )
    else:
        first_u21_year = None
        open_years = []

    first_open_year = (
        open_years[0]
        if open_years
        else None
    )

    if first_u21_year is None:
        outcome = "sans_passage_u21"

    elif first_open_year is None:
        outcome = "u21_sans_open"

    else:
        outcome = "u21_puis_open"

    rider = riders.get(
        rider_id,
        {
            "prenom": "",
            "nom": "",
            "sexe": "",
        },
    )

    rows.append(
        {
            "rider_id_canonique": rider_id,
            "prenom": rider["prenom"],
            "nom": rider["nom"],
            "sexe": rider["sexe"],
            "derniere_annee_u17": last_u17_year,
            "premiere_annee_u21": (
                first_u21_year or ""
            ),
            "premiere_annee_open": (
                first_open_year or ""
            ),
            "issue": outcome,
        }
    )


rows.sort(
    key=lambda row: (
        row["derniere_annee_u17"],
        row["nom"],
        row["prenom"],
    )
)

if not rows:
    raise RuntimeError(
        "Aucune trajectoire disponible."
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
        fieldnames=list(rows[0]),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(rows)


cohort = len(rows)

reached_u21 = sum(
    row["issue"] in (
        "u21_sans_open",
        "u21_puis_open",
    )
    for row in rows
)

reached_open = sum(
    row["issue"] == "u21_puis_open"
    for row in rows
)

without_u21 = sum(
    row["issue"] == "sans_passage_u21"
    for row in rows
)

u21_without_open = sum(
    row["issue"] == "u21_sans_open"
    for row in rows
)


print("=" * 92)
print("ENTONNOIR INDIVIDUEL U17 VERS U21 VERS OPEN")
print("=" * 92)
print(
    "Cohortes retenues : dernières saisons U17 "
    "de 2017 à 2020"
)
print()
print("Sorties de U17                 :", cohort)
print(
    "Passages en U21 sous 3 ans    :",
    f"{reached_u21}/{cohort}",
    f"({100 * reached_u21 / cohort:.1f} %)",
)
print(
    "Passages U21 puis Open        :",
    f"{reached_open}/{cohort}",
    f"({100 * reached_open / cohort:.1f} % de la cohorte U17)",
)
print(
    "Parmi les sportifs en U21     :",
    f"{reached_open}/{reached_u21}",
    (
        f"({100 * reached_open / reached_u21:.1f} %)"
        if reached_u21
        else "-"
    ),
)
print("Sans passage en U21            :", without_u21)
print("U21 sans passage observe Open  :", u21_without_open)
print(
    "Poids d'une personne cohorte  :",
    f"{100 / cohort:.1f} points",
)


print()
print("ENTONNOIR PAR SEXE")

for sex, label in (
    ("F", "Femmes"),
    ("M", "Hommes"),
):
    group = [
        row
        for row in rows
        if row["sexe"] == sex
    ]

    group_u21 = sum(
        row["issue"] in (
            "u21_sans_open",
            "u21_puis_open",
        )
        for row in group
    )

    group_open = sum(
        row["issue"] == "u21_puis_open"
        for row in group
    )

    print()
    print(
        f"{label} : cohorte={len(group)}, "
        f"U21={group_u21}/{len(group)}, "
        f"Open={group_open}/{len(group)}"
    )

    if group:
        print(
            "  Poids d'une personne :",
            f"{100 / len(group):.1f} points",
        )


print()
print("Fichier genere :", OUTPUT_FILE)
