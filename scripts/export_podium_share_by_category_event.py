"""Calcule la part théorique du podium par catégorie, sexe et épreuve."""

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

from observatoire.config import DATABASE_FILE


IDENTITY_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

OUTPUT_FILE = Path(
    "data/exports/podiums_par_categorie_sexe_epreuve_2017_2026.csv"
)

AGE_CLASSES = [
    "U8",
    "U10",
    "U12",
    "U14",
    "U17",
    "U21",
    "OPEN",
    "35+",
    "45+",
    "55+",
    "65+",
    "70+",
    "75+",
]

EVENTS = [
    ("slalom", "Slalom"),
    ("tricks", "Figures"),
    ("jump", "Saut"),
    ("overall", "Combiné"),
]

SEXES = [
    ("F", "Femmes"),
    ("H", "Hommes"),
]


def normalize_category(value):
    category = (value or "").strip().upper()

    legacy = {
        "-10": "U10",
        "-12": "U12",
        "-17": "U17",
    }

    return legacy.get(category, category)


def normalize_sex(value):
    sex = (value or "").strip().upper()

    if sex in ("M", "H"):
        return "H"

    if sex == "F":
        return "F"

    return sex


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
                f"Cycle d'identité pour {rider_id}"
            )

        visited.add(current)
        current = aliases[current]

    return current


def podium_share(participants):
    if participants == 0:
        return ""

    return f"{min(100, 300 / participants):.1f}"


aliases = load_aliases()


with sqlite3.connect(DATABASE_FILE) as database:
    rows = database.execute(
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


for (
    competition_code,
    rider_id,
    event,
    category,
    sex,
) in rows:
    if event not in dict(EVENTS):
        continue

    category = normalize_category(category)
    sex = normalize_sex(sex)

    if category not in AGE_CLASSES:
        continue

    if sex not in ("F", "H"):
        continue

    year = 2000 + int(
        competition_code[:2]
    )

    rider_id = canonical_id(
        rider_id,
        aliases,
    )

    participants[
        (
            year,
            category,
            sex,
            event,
        )
    ].add(rider_id)


output_rows = []


for year in range(2017, 2027):
    for category in AGE_CLASSES:
        for sex, sex_label in SEXES:
            for event, event_label in EVENTS:
                count = len(
                    participants.get(
                        (
                            year,
                            category,
                            sex,
                            event,
                        ),
                        set(),
                    )
                )

                output_rows.append(
                    {
                        "annee": year,
                        "categorie": category,
                        "sexe": sex_label,
                        "epreuve": event_label,
                        "participants": count,
                        "part_theorique_podium_pct": (
                            podium_share(count)
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
        fieldnames=list(output_rows[0]),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(output_rows)


lookup = {
    (
        row["annee"],
        row["categorie"],
        row["sexe"],
        row["epreuve"],
    ): row
    for row in output_rows
}


print("=" * 154)
print("PART THÉORIQUE DU PODIUM PAR CATÉGORIE, SEXE ET ÉPREUVE — 2026")
print("=" * 154)

print(
    f"{'Catégorie':<11}"
    f"{'Sexe':<9}"
    f"{'Slalom':>17}"
    f"{'Figures':>17}"
    f"{'Saut':>17}"
    f"{'Combiné':>17}"
)

print(
    f"{'':<11}"
    f"{'':<9}"
    f"{'N / podium':>17}"
    f"{'N / podium':>17}"
    f"{'N / podium':>17}"
    f"{'N / podium':>17}"
)


for category in AGE_CLASSES:
    for sex_code, sex_label in SEXES:
        values = []

        for event_code, event_label in EVENTS:
            row = lookup[
                (
                    2026,
                    category,
                    sex_label,
                    event_label,
                )
            ]

            count = row["participants"]
            percentage = row[
                "part_theorique_podium_pct"
            ]

            if count == 0:
                display = "0 / —"
            else:
                display = (
                    f"{count} / {percentage} %"
                )

            values.append(display)

        print(
            f"{category:<11}"
            f"{sex_label:<9}"
            + "".join(
                f"{value:>17}"
                for value in values
            )
        )


print()
print("=" * 154)
print("PRÉCISION MÉTHODOLOGIQUE")
print("=" * 154)
print(
    "La part théorique du podium correspond à "
    "min(100 ; 3 / nombre de participants × 100)."
)
print(
    "Elle indique la proportion du champ couverte par les trois "
    "places du podium. Elle ne mesure pas la probabilité sportive "
    "individuelle d'obtenir une médaille."
)
print(
    "Un sportif est compté une seule fois par année dans chaque "
    "champ catégorie × sexe × épreuve."
)
print()
print("Fichier généré :", OUTPUT_FILE)
