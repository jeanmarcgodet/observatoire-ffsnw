"""Integre l'analyse de persistance individuelle dans la note."""

import csv
import statistics
from pathlib import Path

import matplotlib.pyplot as plt


INPUT_FILE = Path(
    "data/exports/persistance_participation_2017_2026.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/persistance_participation_2017_2026.png"
)

START_MARKER = "<!-- BEGIN PERSISTANCE PARTICIPATION -->"
END_MARKER = "<!-- END PERSISTANCE PARTICIPATION -->"


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
    row["nombre_annees"] = int(
        row["nombre_annees"]
    )

    row["annees_set"] = {
        int(year)
        for year in row["annees"].split(",")
        if year
    }


total = len(rows)

year_counts = [
    row["nombre_annees"]
    for row in rows
]

one_year = sum(
    count == 1
    for count in year_counts
)

two_to_three = sum(
    2 <= count <= 3
    for count in year_counts
)

four_to_six = sum(
    4 <= count <= 6
    for count in year_counts
)

seven_to_ten = sum(
    7 <= count <= 10
    for count in year_counts
)

three_or_less = one_year + two_to_three

five_or_more = sum(
    count >= 5
    for count in year_counts
)

all_ten = sum(
    count == 10
    for count in year_counts
)

median_years = statistics.median(
    year_counts
)

mean_years = statistics.mean(
    year_counts
)


cohort_2017 = [
    row
    for row in rows
    if 2017 in row["annees_set"]
]

cohort_2017_present_2026 = [
    row
    for row in cohort_2017
    if 2026 in row["annees_set"]
]


sex_summary = {}

for sex, label in (
    ("F", "Femmes"),
    ("M", "Hommes"),
):
    group = [
        row
        for row in rows
        if row["sexe"] == sex
    ]

    sex_summary[sex] = {
        "label": label,
        "total": len(group),
        "une_annee": sum(
            row["nombre_annees"] == 1
            for row in group
        ),
        "cinq_ou_plus": sum(
            row["nombre_annees"] >= 5
            for row in group
        ),
        "dix_annees": sum(
            row["nombre_annees"] == 10
            for row in group
        ),
    }


labels = [
    "1 année",
    "2 à 3 années",
    "4 à 6 années",
    "7 à 10 années",
]

values = [
    one_year,
    two_to_three,
    four_to_six,
    seven_to_ten,
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(figsize=(10, 6))
plt.bar(labels, values)

plt.title(
    "Nombre d’années de participation observées, 2017-2026"
)
plt.xlabel(
    "Nombre d’années avec au moins une participation"
)
plt.ylabel("Nombre de participants uniques")
plt.grid(axis="y", alpha=0.3)

for index, value in enumerate(values):
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


section_lines = [
    START_MARKER,
    "## Un vivier marqué par une forte rotation",
    "",
    (
        f"Entre 2017 et 2026, **{total} personnes différentes** "
        "ont participé au moins une fois aux Championnats de "
        "France étudiés."
    ),
    "",
    (
        f"La médiane n’est toutefois que de "
        f"**{median_years:.0f} années de participation** "
        f"par personne. La moyenne est de "
        f"**{mean_years:.1f} années**."
    ),
    "",
    "| Nombre d’années observées | Participants |",
    "|---|---:|",
    f"| Une seule année | {one_year} |",
    f"| Deux à trois années | {two_to_three} |",
    f"| Quatre à six années | {four_to_six} |",
    f"| Sept à dix années | {seven_to_ten} |",
    "",
    (
        f"**{one_year} participants sur {total}** ne sont "
        "observés qu’une seule année."
    ),
    "",
    (
        f"Au total, **{three_or_less} personnes sur {total}**, "
        f"soit **{100 * three_or_less / total:.1f} %**, "
        "apparaissent pendant trois années au maximum sur "
        "la période étudiée."
    ),
    "",
    (
        f"À l’inverse, seuls **{seven_to_ten} participants sur "
        f"{total}** sont présents pendant au moins sept années."
    ),
    "",
    (
        f"Seulement **{all_ten} personnes** sont observées "
        "chacune des dix années."
    ),
    "",
    (
        f"**{five_or_more} participants sur {total}** sont "
        "présents pendant au moins cinq années."
    ),
    "",
    (
        "![Persistance individuelle de la participation]"
        "(figures/persistance_participation_2017_2026.png)"
    ),
    "",
    "### La cohorte observée en 2017",
    "",
    (
        f"Parmi les **{len(cohort_2017)} participants présents "
        "en 2017**, seuls "
        f"**{len(cohort_2017_present_2026)} sont également "
        "retrouvés en 2026**."
    ),
    "",
    (
        f"Cela représente "
        f"**{len(cohort_2017_present_2026)} sur "
        f"{len(cohort_2017)}**, soit "
        f"**{100 * len(cohort_2017_present_2026) / len(cohort_2017):.1f} %**."
    ),
    "",
    (
        "Cette présence aux deux extrémités de la période ne "
        "signifie pas que ces personnes ont participé chaque "
        "année entre 2017 et 2026."
    ),
    "",
    "### Lecture par sexe",
    "",
    "| Sexe | Participants uniques | Une seule année | Au moins cinq années | Dix années |",
    "|---|---:|---:|---:|---:|",
]

for sex in ("F", "M"):
    item = sex_summary[sex]

    section_lines.append(
        f"| {item['label']} "
        f"| {item['total']} "
        f"| {item['une_annee']} "
        f"| {item['cinq_ou_plus']} "
        f"| {item['dix_annees']} |"
    )


women = sex_summary["F"]
men = sex_summary["M"]

section_lines.extend(
    [
        "",
        (
            f"Chez les femmes, **{women['cinq_ou_plus']} sur "
            f"{women['total']}** sont présentes pendant au "
            "moins cinq années."
        ),
        "",
        (
            f"Chez les hommes, cette situation concerne "
            f"**{men['cinq_ou_plus']} sur {men['total']}**."
        ),
        "",
        (
            "Ces écarts restent descriptifs. Ils peuvent être "
            "influencés par la structure d’âge, les catégories "
            "et les très faibles effectifs de certaines "
            "épreuves."
        ),
        "",
        "### Interprétation",
        "",
        (
            "La discipline ne repose pas sur un noyau large "
            "et durable de compétiteurs nationaux. Une part "
            "importante des personnes recensées ne participe "
            "que ponctuellement, tandis que le groupe présent "
            "sur une longue durée demeure très réduit."
        ),
        "",
        (
            "Cette rotation contribue à fragiliser la "
            "profondeur des catégories et la continuité entre "
            "les niveaux jeunes, U21 et Open."
        ),
        "",
        (
            "L’absence d’un sportif lors des Championnats de "
            "France ne permet cependant pas de conclure à un "
            "abandon du ski nautique. Elle signifie uniquement "
            "qu’il n’est plus retrouvé dans le périmètre des "
            "compétitions nationales étudiées."
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
print("PERSISTANCE INTEGREE AU RAPPORT")
print("=" * 82)
print("Participants uniques      :", total)
print("Une seule annee           :", one_year)
print("Deux a trois annees       :", two_to_three)
print("Quatre a six annees       :", four_to_six)
print("Sept a dix annees         :", seven_to_ten)
print("Trois annees au maximum  :", three_or_less)
print("Les dix annees            :", all_ten)
print(
    "Presents en 2017 et 2026 :",
    f"{len(cohort_2017_present_2026)}/{len(cohort_2017)}",
)
print("Figure                     :", FIGURE_FILE)
print("Note                       :", REPORT_FILE)
