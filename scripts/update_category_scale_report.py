"""Integre la taille structurelle des categories dans la note."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


INPUT_FILE = Path(
    "data/exports/taille_categories_2017_2026.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/effectif_median_categories_2017_2026.png"
)

START_MARKER = "<!-- BEGIN TAILLE STRUCTURELLE -->"
END_MARKER = "<!-- END TAILLE STRUCTURELLE -->"


def category_sort_key(category: str):
    value = category.strip().upper()

    if value.startswith("U"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )
        return (
            1,
            int(digits) if digits else 999,
        )

    if value == "OPEN":
        return (2, 0)

    if value.endswith("+"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )
        return (
            3,
            int(digits) if digits else 999,
        )

    return (4, 999)


def french_number(value: str) -> str:
    return value.replace(".", ",")


with INPUT_FILE.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    rows = list(
        csv.DictReader(
            handle,
            delimiter=";",
        )
    )


rows.sort(
    key=lambda row: category_sort_key(
        row["categorie"]
    )
)


total_observations = sum(
    int(row["annees_observees"])
    for row in rows
)

under_10 = sum(
    int(row["annees_sous_10"])
    for row in rows
)

under_20 = sum(
    int(row["annees_sous_20"])
    for row in rows
)

under_30 = sum(
    int(row["annees_sous_30"])
    for row in rows
)

at_least_30 = (
    total_observations - under_30
)


labels = [
    (
        "Open"
        if row["categorie"] == "OPEN"
        else row["categorie"]
    )
    for row in rows
]

medians = [
    float(row["effectif_median"])
    for row in rows
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(figsize=(10, 7))
plt.barh(labels, medians)

plt.title(
    "Effectif médian par catégorie nationale, 2017-2026"
)
plt.xlabel("Nombre médian de participants")
plt.ylabel("Catégorie")
plt.grid(axis="x", alpha=0.3)

for index, value in enumerate(medians):
    plt.text(
        value + 0.2,
        index,
        french_number(f"{value:.1f}"),
        va="center",
    )

plt.tight_layout()
plt.savefig(
    FIGURE_FILE,
    dpi=200,
    bbox_inches="tight",
)
plt.close()


table_lines = [
    (
        "| Catégorie | Années observées | "
        "Médiane | Minimum–maximum | "
        "Effectif 2026 | Poids d’une personne en 2026 |"
    ),
    "|---|---:|---:|---:|---:|---:|",
]

for row in rows:
    category = (
        "Open"
        if row["categorie"] == "OPEN"
        else row["categorie"]
    )

    weight = row[
        "poids_une_personne_2026_pct"
    ]

    weight_display = (
        french_number(weight) + " %"
        if weight
        else "—"
    )

    table_lines.append(
        f"| {category} "
        f"| {row['annees_observees']} "
        f"| {french_number(row['effectif_median'])} "
        f"| {row['effectif_minimum']}–"
        f"{row['effectif_maximum']} "
        f"| {row['participants_2026']} "
        f"| {weight_display} |"
    )


section_lines = [
    START_MARKER,
    "## Des effectifs structurellement très faibles",
    "",
    (
        "La faiblesse des effectifs observée en 2026 "
        "n’est pas seulement conjoncturelle. Elle constitue "
        "une caractéristique durable de la pratique "
        "compétitive nationale."
    ),
    "",
    (
        f"Entre 2017 et 2026, la base contient "
        f"**{total_observations} observations "
        "catégorie–année**."
    ),
    "",
    (
        f"Parmi elles, **{under_10} sur "
        f"{total_observations}**, soit "
        f"**{100 * under_10 / total_observations:.1f} %**, "
        "réunissent moins de dix participants."
    ),
    "",
    (
        f"**{under_20} sur {total_observations}**, soit "
        f"**{100 * under_20 / total_observations:.1f} %**, "
        "réunissent moins de vingt participants."
    ),
    "",
    (
        f"**{under_30} sur {total_observations}**, soit "
        f"**{100 * under_30 / total_observations:.1f} %**, "
        "réunissent moins de trente participants."
    ),
    "",
    (
        f"Sur dix saisons, seules **{at_least_30} "
        f"observation catégorie–année sur "
        f"{total_observations}** atteint donc au moins "
        "trente concurrents."
    ),
    "",
    (
        "La catégorie Open, pourtant centrale dans la "
        "continuité sportive vers le plus haut niveau, "
        "présente un effectif médian de seulement "
        "**20 participants**. La médiane est de "
        "**11 en U21**, **13 en U17** et **9 en U14**."
    ),
    "",
    "### Effectifs par catégorie",
    "",
    *table_lines,
    "",
    (
        "![Effectif médian par catégorie]"
        "(figures/effectif_median_categories_2017_2026.png)"
    ),
    "",
    "### Portée de ce constat",
    "",
    (
        "Ces effectifs sont d’autant plus significatifs "
        "que la participation aux Championnats de France "
        "est libre, sans sélection sportive préalable."
    ),
    "",
    (
        "Ils ne décrivent donc pas une élite volontairement "
        "restreinte par des qualifications ou des quotas. "
        "Ils révèlent la très faible profondeur du vivier "
        "compétitif national effectivement mobilisé."
    ),
    "",
    (
        "Dans ces conditions, une variation d’une ou deux "
        "personnes peut modifier fortement les pourcentages "
        "d’une catégorie. Les effectifs bruts et les "
        "dénominateurs doivent toujours précéder "
        "l’interprétation des taux."
    ),
    END_MARKER,
    "",
]

section = "\n".join(section_lines)


report = REPORT_FILE.read_text(
    encoding="utf-8"
)

if (
    START_MARKER in report
    and END_MARKER in report
):
    before = report.split(
        START_MARKER,
        1,
    )[0]

    after = report.split(
        END_MARKER,
        1,
    )[1].lstrip("\n")

    report = before + section + after

else:
    context_marker = (
        "<!-- END CONTEXTE EFFECTIFS -->"
    )

    if context_marker in report:
        report = report.replace(
            context_marker,
            context_marker + "\n\n" + section,
            1,
        )

    else:
        main_marker = "## Principaux résultats"

        if main_marker not in report:
            raise RuntimeError(
                "Point d'insertion introuvable."
            )

        report = report.replace(
            main_marker,
            section + main_marker,
            1,
        )


REPORT_FILE.write_text(
    report,
    encoding="utf-8",
)


print("=" * 82)
print("TAILLE STRUCTURELLE INTEGREE AU RAPPORT")
print("=" * 82)
print(
    "Observations categorie-annee :",
    total_observations,
)
print(
    "Moins de 10 participants    :",
    f"{under_10}/{total_observations}",
)
print(
    "Moins de 20 participants    :",
    f"{under_20}/{total_observations}",
)
print(
    "Moins de 30 participants    :",
    f"{under_30}/{total_observations}",
)
print(
    "Au moins 30 participants    :",
    at_least_30,
)
print("Figure :", FIGURE_FILE)
print("Note   :", REPORT_FILE)
