"""Exporte les indicateurs annuels de participation 2017-2026."""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
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

POPULATION_ORDER = {
    "Jeunes/U21": 1,
    "Open": 2,
    "Seniors": 3,
    "Autres": 4,
    "Tous": 5,
}


def competition_year(code: str) -> int:
    return 2000 + int(code[:2])


def population_from_category(category: str) -> str:
    value = (category or "").strip().upper()

    if value.startswith("U"):
        return "Jeunes/U21"

    if value == "OPEN":
        return "Open"

    if value.endswith("+"):
        return "Seniors"

    return "Autres"


def percentage(
    numerator: int,
    denominator: int,
) -> str:
    if denominator == 0:
        return ""

    return f"{100 * numerator / denominator:.1f}"


def load_identity_map() -> dict[int, int]:
    if not IDENTITY_FILE.exists():
        raise FileNotFoundError(
            f"Fichier absent: {IDENTITY_FILE}"
        )

    alias_map = {}

    with IDENTITY_FILE.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(
            handle,
            delimiter=";",
        ):
            alias_map[
                int(row["alias_rider_id"])
            ] = int(
                row["canonical_rider_id"]
            )

    return alias_map


def canonical_rider(
    rider_id: int,
    alias_map: dict[int, int],
) -> int:
    visited = set()
    current = rider_id

    while current in alias_map:
        if current in visited:
            raise RuntimeError(
                f"Cycle d'identite pour {rider_id}"
            )

        visited.add(current)
        current = alias_map[current]

    return current


def main() -> None:
    alias_map = load_identity_map()

    output_directory = Path("data/exports")
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    annual_file = (
        output_directory
        / "participation_annuelle_2017_2026.csv"
    )

    categories_file = (
        output_directory
        / "participation_categories_2017_2026.csv"
    )

    placeholders = ",".join(
        "?" for _ in COMPETITION_CODES
    )

    with sqlite3.connect(DATABASE_FILE) as database:
        rows = database.execute(
            f"""
            SELECT
                c.iwwf_id,
                e.rider_id,
                e.categorie,
                COALESCE(r.sexe, '')
            FROM entries e
            JOIN competitions c
              ON c.id = e.competition_id
            JOIN riders r
              ON r.id = e.rider_id
            WHERE c.iwwf_id IN ({placeholders})
            ORDER BY
                c.iwwf_id,
                e.rider_id,
                e.categorie
            """,
            COMPETITION_CODES,
        ).fetchall()

    participants = defaultdict(set)
    entries = defaultdict(int)
    sexes = {}
    category_participants = defaultdict(set)

    for code, rider_id, category, sex in rows:
        year = competition_year(code)
        population = population_from_category(
            category
        )

        canonical_id = canonical_rider(
            rider_id,
            alias_map,
        )

        normalized_sex = sex.strip().upper()
        previous_sex = sexes.get(canonical_id)

        if (
            previous_sex
            and normalized_sex
            and previous_sex != normalized_sex
        ):
            raise RuntimeError(
                "Sexes contradictoires pour "
                f"le rider canonique {canonical_id}"
            )

        if normalized_sex:
            sexes[canonical_id] = normalized_sex

        participants[
            (year, population)
        ].add(canonical_id)

        participants[
            (year, "Tous")
        ].add(canonical_id)

        entries[(year, population)] += 1
        entries[(year, "Tous")] += 1

        category_participants[
            (year, category, population)
        ].add(canonical_id)

    first_year_all = {}

    for year in range(2017, 2027):
        for rider_id in participants.get(
            (year, "Tous"),
            set(),
        ):
            first_year_all.setdefault(
                rider_id,
                year,
            )

    first_year_population = {}

    for (
        year,
        population,
    ), rider_ids in sorted(
        participants.items()
    ):
        if population == "Tous":
            continue

        for rider_id in rider_ids:
            first_year_population.setdefault(
                (rider_id, population),
                year,
            )

    annual_rows = []

    for year in range(2017, 2027):
        populations = {
            population
            for candidate_year, population
            in participants
            if candidate_year == year
        }

        for population in sorted(
            populations,
            key=lambda value: (
                POPULATION_ORDER.get(value, 99)
            ),
        ):
            rider_ids = participants[
                (year, population)
            ]

            previous_ids = participants.get(
                (year - 1, population),
                set(),
            )

            retained = rider_ids & previous_ids

            women = sum(
                sexes.get(rider_id) == "F"
                for rider_id in rider_ids
            )

            men = sum(
                sexes.get(rider_id) == "M"
                for rider_id in rider_ids
            )

            unknown = (
                len(rider_ids) - women - men
            )

            new_all = sum(
                first_year_all[rider_id] == year
                for rider_id in rider_ids
            )

            if population == "Tous":
                new_population = new_all
            else:
                new_population = sum(
                    first_year_population[
                        (rider_id, population)
                    ] == year
                    for rider_id in rider_ids
                )

            annual_rows.append(
                {
                    "annee": year,
                    "population": population,
                    "participants": len(rider_ids),
                    "femmes": women,
                    "hommes": men,
                    "sexe_non_renseigne": unknown,
                    "taux_femmes_pct": percentage(
                        women,
                        len(rider_ids),
                    ),
                    "inscriptions": entries[
                        (year, population)
                    ],
                    "nouveaux_dans_base": new_all,
                    "nouveaux_dans_population": (
                        new_population
                    ),
                    "presents_annee_precedente": (
                        len(retained)
                    ),
                    "participants_annee_precedente": (
                        len(previous_ids)
                    ),
                    "taux_fidelisation_pct": (
                        percentage(
                            len(retained),
                            len(previous_ids),
                        )
                    ),
                }
            )

    with annual_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(annual_rows[0]),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(annual_rows)

    category_rows = []

    for (
        year,
        category,
        population,
    ), rider_ids in sorted(
        category_participants.items(),
        key=lambda item: (
            item[0][0],
            POPULATION_ORDER.get(
                item[0][2],
                99,
            ),
            item[0][1],
        ),
    ):
        women = sum(
            sexes.get(rider_id) == "F"
            for rider_id in rider_ids
        )

        men = sum(
            sexes.get(rider_id) == "M"
            for rider_id in rider_ids
        )

        category_rows.append(
            {
                "annee": year,
                "population": population,
                "categorie": category,
                "participants": len(rider_ids),
                "femmes": women,
                "hommes": men,
                "taux_femmes_pct": percentage(
                    women,
                    len(rider_ids),
                ),
            }
        )

    with categories_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(category_rows[0]),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(category_rows)

    print("=" * 88)
    print("PARTICIPATION CANONIQUE 2017-2026")
    print("=" * 88)

    for row in annual_rows:
        if row["population"] != "Tous":
            continue

        fidelity = (
            row["taux_fidelisation_pct"]
            or "-"
        )

        print(
            f"{row['annee']} "
            f"participants={row['participants']:<3} "
            f"femmes={row['femmes']:<3} "
            f"hommes={row['hommes']:<3} "
            f"nouveaux={row['nouveaux_dans_base']:<3} "
            f"fidelisation={fidelity}%"
        )

    print()
    print("Alias appliques :", len(alias_map))
    print("Fichiers generes :")
    print(" -", annual_file)
    print(" -", categories_file)


if __name__ == "__main__":
    main()
