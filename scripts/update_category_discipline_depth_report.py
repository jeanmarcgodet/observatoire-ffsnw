"""Integre la profondeur des epreuves dans la note d'analyse."""

import csv
import statistics
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


INPUT_FILE = Path(
    "data/exports/profondeur_epreuves_categories_2017_2026.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/profondeur_champs_categories_disciplines_2017_2026.png"
)

START_MARKER = "<!-- BEGIN PROFONDEUR EPREUVES -->"
END_MARKER = "<!-- END PROFONDEUR EPREUVES -->"

DISCIPLINE_LABELS = {
    "slalom": "Slalom",
    "tricks": "Figures",
    "jump": "Saut",
}


def category_sort_key(category):
    value = category.upper()

    if value.startswith("U"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )
        return (1, int(digits) if digits else 999)

    if value == "OPEN":
        return (2, 0)

    if value.endswith("+"):
        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )
        return (3, int(digits) if digits else 999)

    return (4, 999)


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


for row in rows:
    row["annee"] = int(row["annee"])
    row["participants"] = int(
        row["participants"]
    )


values = [
    row["participants"]
    for row in rows
]

total = len(values)

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

disputed = total - empty
podium_or_less = empty + one_to_three
under_ten = empty + one_to_three + four_to_nine
under_twenty = under_ten + ten_to_nineteen


labels = [
    "0",
    "1 à 3",
    "4 à 9",
    "10 à 19",
    "20 et plus",
]

counts = [
    empty,
    one_to_three,
    four_to_nine,
    ten_to_nineteen,
    twenty_or_more,
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(figsize=(10, 6))
plt.bar(labels, counts)

plt.title(
    "Taille des champs catégorie–discipline, 2017-2026"
)
plt.xlabel("Nombre de participants dans le champ")
plt.ylabel("Nombre de champs catégorie–discipline")
plt.grid(axis="y", alpha=0.3)

for index, value in enumerate(counts):
    plt.text(
        index,
        value + 2,
        str(value),
        ha="center",
    )

plt.tight_layout()
plt.savefig(
    FIGURE_FILE,
    dpi=200,
    bbox_inches="tight",
)
plt.close()


discipline_summary = {}

for discipline, label in DISCIPLINE_LABELS.items():
    discipline_values = [
        row["participants"]
        for row in rows
        if row["discipline"] == discipline
    ]

    nonzero = [
        value
        for value in discipline_values
        if value > 0
    ]

    discipline_summary[discipline] = {
        "label": label,
        "champs": len(discipline_values),
        "vides": sum(
            value == 0
            for value in discipline_values
        ),
        "mediane": statistics.median(
            discipline_values
        ),
        "mediane_non_vide": statistics.median(
            nonzero
        ),
        "maximum": max(
            discipline_values
        ),
    }


rows_2026 = [
    row
    for row in rows
    if row["annee"] == 2026
]

categories_2026 = sorted(
    {
        row["categorie"]
        for row in rows_2026
    },
    key=category_sort_key,
)

lookup_2026 = {
    (
        row["categorie"],
        row["discipline"],
    ): row["participants"]
    for row in rows_2026
}


table_2026 = [
    "| Catégorie | Slalom | Figures | Saut |",
    "|---|---:|---:|---:|",
]

for category in categories_2026:
    display_category = (
        "Open"
        if category == "OPEN"
        else category
    )

    table_2026.append(
        f"| {display_category} "
        f"| {lookup_2026[(category, 'slalom')]} "
        f"| {lookup_2026[(category, 'tricks')]} "
        f"| {lookup_2026[(category, 'jump')]} |"
    )


open_slalom = lookup_2026[
    ("OPEN", "slalom")
]

open_tricks = lookup_2026[
    ("OPEN", "tricks")
]

open_jump = lookup_2026[
    ("OPEN", "jump")
]


section_lines = [
    START_MARKER,
    "## Des épreuves nationales souvent réduites à quelques concurrents",
    "",
    (
        "Le nombre total de participants masque une "
        "fragmentation supplémentaire entre les catégories "
        "et les trois disciplines : slalom, figures et saut."
    ),
    "",
    (
        "Un « champ catégorie–discipline » correspond ici "
        "à une catégorie nationale observée une année, "
        "croisée avec chacune des trois disciplines."
    ),
    "",
    (
        f"Entre 2017 et 2026, **{total} champs potentiels** "
        "sont ainsi observés."
    ),
    "",
    (
        f"**{empty} champs sur {total}** ne comptent aucun "
        "participant dans la discipline considérée."
    ),
    "",
    (
        f"**{one_to_three} champs** ne réunissent que "
        "**un à trois participants**."
    ),
    "",
    (
        f"En incluant les champs vides, **{podium_or_less} "
        f"champs sur {total}**, soit "
        f"**{100 * podium_or_less / total:.1f} %**, "
        "comptent au maximum trois participants."
    ),
    "",
    (
        f"Parmi les **{disputed} champs effectivement "
        f"disputés**, **{one_to_three}**, soit "
        f"**{100 * one_to_three / disputed:.1f} %**, "
        "ne dépassent pas trois concurrents."
    ),
    "",
    (
        f"**{under_ten} champs sur {total}**, soit "
        f"**{100 * under_ten / total:.1f} %**, "
        "comptent moins de dix participants."
    ),
    "",
    (
        f"**{under_twenty} champs sur {total}**, soit "
        f"**{100 * under_twenty / total:.1f} %**, "
        "comptent moins de vingt participants."
    ),
    "",
    (
        f"Seuls **{twenty_or_more} champs sur {total}** "
        "atteignent vingt participants ou davantage."
    ),
    "",
    "### Profondeur médiane par discipline",
    "",
    "| Discipline | Champs | Champs vides | Médiane tous champs | Médiane champs disputés | Maximum |",
    "|---|---:|---:|---:|---:|---:|",
]

for discipline in (
    "slalom",
    "tricks",
    "jump",
):
    item = discipline_summary[discipline]

    section_lines.append(
        f"| {item['label']} "
        f"| {item['champs']} "
        f"| {item['vides']} "
        f"| {item['mediane']:.1f} "
        f"| {item['mediane_non_vide']:.1f} "
        f"| {item['maximum']} |"
    )


section_lines.extend(
    [
        "",
        (
            "Parmi les champs effectivement disputés, "
            "l’effectif médian est de **8 participants en "
            "slalom**, mais seulement de **4 en figures** "
            "et de **4 en saut**."
        ),
        "",
        "### Situation observée en 2026",
        "",
        *table_2026,
        "",
        (
            "La catégorie Open ne réunit en 2026 que "
            f"**{open_slalom} concurrents en slalom**, "
            f"**{open_tricks} en figures** et "
            f"**{open_jump} en saut**."
        ),
        "",
        (
            "Une seule personne représente donc "
            f"**{100 / open_slalom:.1f} %** du champ Open "
            "en slalom, "
            f"**{100 / open_tricks:.1f} %** en figures et "
            f"**{100 / open_jump:.1f} %** en saut."
        ),
        "",
        (
            "![Profondeur des champs catégorie–discipline]"
            "(figures/profondeur_champs_categories_disciplines_2017_2026.png)"
        ),
        "",
        "### Interprétation",
        "",
        (
            "Ces résultats montrent que la faiblesse du "
            "vivier national ne tient pas seulement au nombre "
            "global de participants. Elle est accentuée par "
            "la fragmentation des sportifs entre de nombreuses "
            "catégories et plusieurs disciplines."
        ),
        "",
        (
            "Dans de nombreux champs, le nombre de concurrents "
            "est égal ou inférieur au nombre de places sur un "
            "podium."
        ),
        "",
        (
            "La participation aux Championnats de France "
            "étant libre, sans sélection préalable, cette "
            "situation révèle une profondeur compétitive "
            "nationale extrêmement limitée."
        ),
        END_MARKER,
        "",
    ]
)

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
    insertion_marker = "## Conclusion provisoire"

    if insertion_marker not in report:
        raise RuntimeError(
            "Section Conclusion provisoire introuvable."
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
print("PROFONDEUR DES EPREUVES INTEGREE")
print("=" * 82)
print("Champs potentiels        :", total)
print("Champs vides             :", empty)
print("De 1 a 3 participants   :", one_to_three)
print(
    "Maximum 3, vides inclus :",
    f"{podium_or_less}/{total}",
)
print(
    "Maximum 3, champs joues :",
    f"{one_to_three}/{disputed}",
)
print("Moins de 10             :", under_ten)
print("Moins de 20             :", under_twenty)
print("20 et plus              :", twenty_or_more)
print("Figure                   :", FIGURE_FILE)
print("Note                     :", REPORT_FILE)
