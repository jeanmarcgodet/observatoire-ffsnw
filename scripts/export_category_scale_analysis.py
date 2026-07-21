"""Analyse la taille structurelle des categories nationales."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path(
    "data/exports/participation_categories_2017_2026.csv"
)

OUTPUT_FILE = Path(
    "data/exports/taille_categories_2017_2026.csv"
)

YEARS = tuple(range(2017, 2027))


def category_sort_key(category: str):
    value = (category or "").strip().upper()

    if value.startswith("U"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )

        return (
            1,
            int(digits) if digits else 999,
            value,
        )

    if value == "OPEN":
        return (2, 0, value)

    if value.endswith("+"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )

        return (
            3,
            int(digits) if digits else 999,
            value,
        )

    return (4, 0, value)


def structural_label(median_value: float) -> str:
    if median_value < 10:
        return "moins_de_10"

    if median_value < 20:
        return "moins_de_20"

    if median_value < 30:
        return "moins_de_30"

    return "30_et_plus"


if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)


with INPUT_FILE.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    source_rows = list(
        csv.DictReader(
            handle,
            delimiter=";",
        )
    )


annual_categories = defaultdict(
    lambda: {
        "participants": 0,
        "femmes": 0,
        "hommes": 0,
    }
)

for row in source_rows:
    year = int(row["annee"])
    category = row["categorie"].strip().upper()

    legacy_categories = {
        "-10": "U10",
        "-12": "U12",
        "-17": "U17",
    }

    category = legacy_categories.get(
        category,
        category,
    )

    key = (year, category)

    annual_categories[key]["participants"] += int(
        row["participants"]
    )

    annual_categories[key]["femmes"] += int(
        row["femmes"]
    )

    annual_categories[key]["hommes"] += int(
        row["hommes"]
    )


categories = sorted(
    {
        category
        for year, category in annual_categories
    },
    key=category_sort_key,
)


summary_rows = []

for category in categories:
    observations = [
        (
            year,
            annual_categories[
                (year, category)
            ]["participants"],
        )
        for year in YEARS
        if (year, category) in annual_categories
    ]

    values = [
        participants
        for year, participants in observations
    ]

    observed_years = len(values)
    median_value = statistics.median(values)
    mean_value = statistics.mean(values)
    minimum = min(values)
    maximum = max(values)

    participants_2026 = (
        annual_categories[
            (2026, category)
        ]["participants"]
        if (2026, category) in annual_categories
        else 0
    )

    one_person_weight_2026 = (
        100 / participants_2026
        if participants_2026
        else None
    )

    years_under_10 = sum(
        value < 10
        for value in values
    )

    years_under_20 = sum(
        value < 20
        for value in values
    )

    years_under_30 = sum(
        value < 30
        for value in values
    )

    summary_rows.append(
        {
            "categorie": category,
            "annees_observees": observed_years,
            "effectif_median": f"{median_value:.1f}",
            "effectif_moyen": f"{mean_value:.1f}",
            "effectif_minimum": minimum,
            "effectif_maximum": maximum,
            "participants_2026": participants_2026,
            "poids_une_personne_2026_pct": (
                f"{one_person_weight_2026:.1f}"
                if one_person_weight_2026
                is not None
                else ""
            ),
            "annees_sous_10": years_under_10,
            "annees_sous_20": years_under_20,
            "annees_sous_30": years_under_30,
            "niveau_structurel": structural_label(
                median_value
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
        fieldnames=list(summary_rows[0]),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(summary_rows)


category_year_values = [
    data["participants"]
    for data in annual_categories.values()
]

total_observations = len(category_year_values)

under_10 = sum(
    value < 10
    for value in category_year_values
)

under_20 = sum(
    value < 20
    for value in category_year_values
)

under_30 = sum(
    value < 30
    for value in category_year_values
)


print("=" * 112)
print("TAILLE STRUCTURELLE DES CATEGORIES NATIONALES 2017-2026")
print("=" * 112)

print(
    f"{'Categorie':<12}"
    f"{'Annees':>8}"
    f"{'Mediane':>10}"
    f"{'Moyenne':>10}"
    f"{'Min':>7}"
    f"{'Max':>7}"
    f"{'2026':>7}"
    f"{'Poids 1 pers.':>16}"
)

for row in summary_rows:
    weight = (
        row["poids_une_personne_2026_pct"]
        + " %"
        if row[
            "poids_une_personne_2026_pct"
        ]
        else "-"
    )

    print(
        f"{row['categorie']:<12}"
        f"{row['annees_observees']:>8}"
        f"{row['effectif_median']:>10}"
        f"{row['effectif_moyen']:>10}"
        f"{row['effectif_minimum']:>7}"
        f"{row['effectif_maximum']:>7}"
        f"{row['participants_2026']:>7}"
        f"{weight:>16}"
    )


print()
print("=" * 112)
print("FREQUENCE DES TRES FAIBLES EFFECTIFS")
print("=" * 112)
print(
    "Observations categorie-annee :",
    total_observations,
)
print(
    "Moins de 10 participants    :",
    f"{under_10}/{total_observations}",
    f"({100 * under_10 / total_observations:.1f} %)",
)
print(
    "Moins de 20 participants    :",
    f"{under_20}/{total_observations}",
    f"({100 * under_20 / total_observations:.1f} %)",
)
print(
    "Moins de 30 participants    :",
    f"{under_30}/{total_observations}",
    f"({100 * under_30 / total_observations:.1f} %)",
)

print()
print("Fichier genere :", OUTPUT_FILE)
