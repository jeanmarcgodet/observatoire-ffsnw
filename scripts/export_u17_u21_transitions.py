"""Analyse les trajectoires U17 vers U21."""

import csv
import sqlite3
from collections import Counter, defaultdict
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
    "data/exports/trajectoires_u17_u21_2017_2023.csv"
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
        for (
            rider_id,
            first_name,
            last_name,
            sex,
        ) in database.execute(
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


trajectories = []

for rider_id, rider_observations in observations.items():
    u17_years = {
        year
        for year, category in rider_observations
        if category == "U17"
    }

    if not u17_years:
        continue

    last_u17_year = max(u17_years)

    # Trois saisons completes de recul.
    if last_u17_year > 2023:
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

    future_observations = {
        (year, category)
        for year, category in rider_observations
        if last_u17_year
        < year
        <= last_u17_year + 3
    }

    if u21_years:
        first_u21_year = u21_years[0]
        delay = first_u21_year - last_u17_year
        outcome = "passage_u21"

    elif future_observations:
        first_u21_year = ""
        delay = ""
        outcome = "autre_continuite"

    else:
        first_u21_year = ""
        delay = ""
        outcome = "disparition_observee"

    rider = riders.get(
        rider_id,
        {
            "prenom": "",
            "nom": "",
            "sexe": "",
        },
    )

    trajectories.append(
        {
            "rider_id_canonique": rider_id,
            "prenom": rider["prenom"],
            "nom": rider["nom"],
            "sexe": rider["sexe"],
            "derniere_annee_u17": last_u17_year,
            "premiere_annee_u21": first_u21_year,
            "delai_vers_u21": delay,
            "issue_sous_trois_ans": outcome,
        }
    )


trajectories.sort(
    key=lambda row: (
        row["derniere_annee_u17"],
        row["nom"],
        row["prenom"],
    )
)

if not trajectories:
    raise RuntimeError(
        "Aucune trajectoire U17 detectee."
    )


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fieldnames = [
    "rider_id_canonique",
    "prenom",
    "nom",
    "sexe",
    "derniere_annee_u17",
    "premiere_annee_u21",
    "delai_vers_u21",
    "issue_sous_trois_ans",
]

with OUTPUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(trajectories)


print("=" * 98)
print("TRANSITION U17 VERS U21 SOUS TROIS ANS")
print("=" * 98)

all_delays = Counter()

for cohort_year in range(2017, 2024):
    cohort = [
        row
        for row in trajectories
        if row["derniere_annee_u17"]
        == cohort_year
    ]

    delays = Counter(
        int(row["delai_vers_u21"])
        for row in cohort
        if row["issue_sous_trois_ans"]
        == "passage_u21"
    )

    all_delays.update(delays)

    passages = sum(delays.values())

    other = sum(
        row["issue_sous_trois_ans"]
        == "autre_continuite"
        for row in cohort
    )

    disappeared = sum(
        row["issue_sous_trois_ans"]
        == "disparition_observee"
        for row in cohort
    )

    rate = (
        100 * passages / len(cohort)
        if cohort
        else 0
    )

    print(
        f"{cohort_year} "
        f"cohorte={len(cohort):>2} "
        f"vers_U21={passages:>2} "
        f"({rate:>5.1f} %) "
        f"autre={other:>2} "
        f"non_retrouves={disappeared:>2}"
    )


cohort_total = len(trajectories)

total_passages = sum(
    row["issue_sous_trois_ans"]
    == "passage_u21"
    for row in trajectories
)

total_other = sum(
    row["issue_sous_trois_ans"]
    == "autre_continuite"
    for row in trajectories
)

total_disappeared = sum(
    row["issue_sous_trois_ans"]
    == "disparition_observee"
    for row in trajectories
)


print()
print("=" * 98)
print("TOTAL U17 VERS U21")
print("=" * 98)
print("Sorties observees de U17 :", cohort_total)
print("Passage la meme annee    :", all_delays[0])
print("Passage a un an          :", all_delays[1])
print("Passage a deux ans       :", all_delays[2])
print("Passage a trois ans      :", all_delays[3])
print("Passages totaux          :", total_passages)
print(
    "Taux de passage          :",
    (
        f"{total_passages}/{cohort_total} "
        f"({100 * total_passages / cohort_total:.1f} %)"
    ),
)
print("Autre continuite         :", total_other)
print("Non retrouves            :", total_disappeared)
print(
    "Poids d'une personne     :",
    f"{100 / cohort_total:.1f} points",
)


print()
print("TRANSITION U17 VERS U21 PAR SEXE")

for sex, label in (
    ("F", "Femmes"),
    ("M", "Hommes"),
):
    group = [
        row
        for row in trajectories
        if row["sexe"] == sex
    ]

    transitions = sum(
        row["issue_sous_trois_ans"]
        == "passage_u21"
        for row in group
    )

    rate = (
        100 * transitions / len(group)
        if group
        else 0
    )

    weight = (
        100 / len(group)
        if group
        else 0
    )

    print(
        f"{label:<7}: "
        f"{transitions}/{len(group)} "
        f"({rate:.1f} %) "
        f"- une personne = {weight:.1f} points"
    )


print()
print("Fichier genere :", OUTPUT_FILE)
