"""Ajoute le contexte de faibles effectifs à la note d'analyse."""

from __future__ import annotations

import csv
from pathlib import Path


ANNUAL_FILE = Path(
    "data/exports/participation_annuelle_2017_2026.csv"
)

CATEGORY_FILE = Path(
    "data/exports/participation_categories_2017_2026.csv"
)

TRANSITION_FILE = Path(
    "data/exports/trajectoires_jeunes_open_2017_2023.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

START_MARKER = "<!-- BEGIN CONTEXTE EFFECTIFS -->"
END_MARKER = "<!-- END CONTEXTE EFFECTIFS -->"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        return list(
            csv.DictReader(
                handle,
                delimiter=";",
            )
        )


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


annual_rows = read_csv(ANNUAL_FILE)
category_rows = read_csv(CATEGORY_FILE)
transition_rows = read_csv(TRANSITION_FILE)


annual_2026 = {
    row["population"]: row
    for row in annual_rows
    if row["annee"] == "2026"
}

total_2026 = int(
    annual_2026["Tous"]["participants"]
)

open_2026 = int(
    annual_2026["Open"]["participants"]
)

senior_2026 = int(
    annual_2026["Seniors"]["participants"]
)

youth_2026 = int(
    annual_2026["Jeunes/U21"]["participants"]
)


u21_rows = [
    row
    for row in transition_rows
    if row["derniere_categorie_jeune"] == "U21"
]

u21_total = len(u21_rows)

u21_open = sum(
    row["issue_sous_trois_ans"]
    == "passage_open"
    for row in u21_rows
)

u21_women = [
    row
    for row in u21_rows
    if row["sexe"] == "F"
]

u21_women_open = sum(
    row["issue_sous_trois_ans"]
    == "passage_open"
    for row in u21_women
)


categories_2026 = sorted(
    (
        row
        for row in category_rows
        if row["annee"] == "2026"
    ),
    key=lambda row: category_sort_key(
        row["categorie"]
    ),
)


category_table = [
    "| Catégorie | Participants | Femmes | Hommes |",
    "|---|---:|---:|---:|",
]

for row in categories_2026:
    category_table.append(
        f"| {row['categorie']} "
        f"| {row['participants']} "
        f"| {row['femmes']} "
        f"| {row['hommes']} |"
    )


section_lines = [
    START_MARKER,
    "## Une population compétitive nationale très réduite",
    "",
    (
        f"En 2026, les compétitions nationales étudiées "
        f"rassemblent seulement **{total_2026} participants "
        "uniques**, toutes catégories confondues."
    ),
    "",
    (
        "Ce chiffre ne représente pas l’ensemble des licenciés "
        "ou des pratiquants de ski nautique. Il mesure le vivier "
        "compétitif national effectivement présent aux "
        "Championnats de France."
    ),
    "",
    (
        "La participation à ces championnats étant libre, sans "
        "sélection sportive préalable, les faibles effectifs "
        "observés ne peuvent pas être expliqués par un système "
        "de qualification, des quotas ou une limitation du "
        "nombre de participants."
    ),
    "",
    (
        "Ils témoignent donc de la très faible profondeur de la "
        "pratique compétitive nationale observable."
    ),
    "",
    "### Effectifs nationaux observés en 2026",
    "",
    (
        f"Les grandes populations comptent "
        f"**{youth_2026} Jeunes/U21**, "
        f"**{open_2026} Open** et "
        f"**{senior_2026} Seniors**."
    ),
    "",
    (
        "La somme de ces populations peut légèrement dépasser "
        "le nombre de participants uniques lorsqu’un même "
        "sportif apparaît dans plusieurs catégories au cours "
        "de la saison."
    ),
    "",
    *category_table,
    "",
    "### Conséquence sur l’interprétation des pourcentages",
    "",
    (
        f"Dans la catégorie Open, qui ne compte que "
        f"**{open_2026} participants en 2026**, une seule "
        f"personne représente **{100 / open_2026:.1f} %** "
        "de l’effectif."
    ),
    "",
    (
        f"Chez les Seniors, une personne représente "
        f"**{100 / senior_2026:.1f} %** des "
        f"{senior_2026} participants observés."
    ),
    "",
    (
        f"Le taux de passage U21 vers Open est de "
        f"**{u21_open} sur {u21_total}**, soit "
        f"**{100 * u21_open / u21_total:.1f} %**. "
        f"Une seule transition supplémentaire ou en moins "
        f"modifie ce taux de **{100 / u21_total:.1f} points**."
    ),
    "",
    (
        f"Chez les femmes, le résultat repose sur seulement "
        f"**{u21_women_open} passages sur "
        f"{len(u21_women)} sportives**. Une seule personne "
        f"représente alors **{100 / len(u21_women):.1f} "
        "points de pourcentage**."
    ),
    "",
    "### Règle de présentation retenue",
    "",
    (
        "Les résultats doivent donc toujours être présentés "
        "sous la forme **effectif / population totale**, puis "
        "éventuellement en pourcentage."
    ),
    "",
    (
        "Pour les groupes de moins de 30 personnes, les "
        "pourcentages sont considérés comme descriptifs et "
        "doivent être interprétés avec prudence."
    ),
    "",
    (
        "Pour les groupes de moins de 10 personnes, aucun "
        "pourcentage ne doit être commenté indépendamment "
        "de l’effectif brut correspondant."
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

    report = (
        before
        + section
        + after
    )
else:
    insertion_marker = "## Principaux résultats"

    if insertion_marker not in report:
        raise RuntimeError(
            "Section Principaux résultats introuvable."
        )

    report = report.replace(
        insertion_marker,
        section + insertion_marker,
        1,
    )


REPORT_FILE.write_text(
    report,
    encoding="utf-8",
)


print("=" * 82)
print("CONTEXTE DES EFFECTIFS INTEGRE")
print("=" * 82)
print("Participants uniques 2026 :", total_2026)
print("Jeunes/U21              :", youth_2026)
print("Open                     :", open_2026)
print("Seniors                  :", senior_2026)
print(
    "Transition U21 vers Open :",
    f"{u21_open}/{u21_total}",
)
print(
    "Transition femmes        :",
    f"{u21_women_open}/{len(u21_women)}",
)
print("Note mise a jour          :", REPORT_FILE)
