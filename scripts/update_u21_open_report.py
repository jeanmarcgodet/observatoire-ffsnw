"""Ajoute l'analyse U21 vers Open à la note principale."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


INPUT_FILE = Path(
    "data/exports/trajectoires_jeunes_open_2017_2023.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/transition_u21_open_2017_2023.png"
)

START_MARKER = "<!-- BEGIN TRANSITION U21 OPEN -->"
END_MARKER = "<!-- END TRANSITION U21 OPEN -->"


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


u21_rows = [
    row
    for row in rows
    if row["derniere_categorie_jeune"] == "U21"
]

delays = Counter(
    int(row["delai_vers_open"])
    for row in u21_rows
    if row["issue_sous_trois_ans"] == "passage_open"
)

disappeared = sum(
    row["issue_sous_trois_ans"]
    == "disparition_observee"
    for row in u21_rows
)

other = sum(
    row["issue_sous_trois_ans"]
    == "autre_continuite"
    for row in u21_rows
)

women = [
    row
    for row in u21_rows
    if row["sexe"] == "F"
]

men = [
    row
    for row in u21_rows
    if row["sexe"] == "F"
]

men = [
    row
    for row in u21_rows
    if row["sexe"] == "M"
]

women_open = sum(
    row["issue_sous_trois_ans"] == "passage_open"
    for row in women
)

men_open = sum(
    row["issue_sous_trois_ans"] == "passage_open"
    for row in men
)

open_total = sum(delays.values())
cohort_total = len(u21_rows)

open_rate = (
    100 * open_total / cohort_total
    if cohort_total
    else 0
)

disappearance_rate = (
    100 * disappeared / cohort_total
    if cohort_total
    else 0
)


labels = [
    "Même année",
    "À 1 an",
    "À 2 ans",
    "À 3 ans",
    "Non retrouvés",
]

values = [
    delays[0],
    delays[1],
    delays[2],
    delays[3],
    disappeared,
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(figsize=(10, 6))
plt.bar(labels, values)

plt.title(
    "Trajectoire après la dernière saison U21"
)
plt.xlabel("Issue observée sous trois ans")
plt.ylabel("Nombre de sportifs")
plt.ylim(0, max(values) + 4)
plt.grid(axis="y", alpha=0.3)

for index, value in enumerate(values):
    plt.text(
        index,
        value + 0.3,
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
    "## Transition de la catégorie U21 vers l’Open",
    "",
    (
        "L’analyse porte sur les sportifs dont la dernière "
        "participation observée en U21 se situe entre 2017 "
        "et 2023. Cette borne permet de disposer de trois "
        "années complètes de recul."
    ),
    "",
    (
        f"Sur **{cohort_total} sorties observées de U21**, "
        f"**{open_total} sportifs apparaissent ensuite en "
        f"Open dans un délai maximal de trois ans**, soit "
        f"**{open_rate:.1f} %**."
    ),
    "",
    (
        f"À l’inverse, **{disappeared} sportifs**, soit "
        f"**{disappearance_rate:.1f} %**, ne sont plus "
        "retrouvés dans les championnats nationaux étudiés "
        "sur cette période."
    ),
    "",
    (
        "Cette absence ne signifie pas nécessairement un "
        "arrêt complet de la pratique ; elle indique une "
        "sortie du périmètre compétitif national observé."
    ),
    "",
    "### Délai du passage vers l’Open",
    "",
    "| Délai | Sportifs |",
    "|---|---:|",
    f"| Même année | {delays[0]} |",
    f"| Un an | {delays[1]} |",
    f"| Deux ans | {delays[2]} |",
    f"| Trois ans | {delays[3]} |",
    f"| Non retrouvés | {disappeared} |",
    "",
    (
        f"Chez les femmes, **{women_open} sur {len(women)}** "
        "passent en Open, soit "
        f"**{100 * women_open / len(women):.1f} %**."
    ),
    "",
    (
        f"Chez les hommes, **{men_open} sur {len(men)}** "
        "passent en Open, soit "
        f"**{100 * men_open / len(men):.1f} %**."
    ),
    "",
    (
        "![Transition U21 vers Open]"
        "(figures/transition_u21_open_2017_2023.png)"
    ),
    "",
    (
        "La transition entre U21 et Open constitue ainsi "
        "un point de fragilité majeur de la continuité "
        "compétitive nationale."
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
    conclusion_marker = (
        "## Conclusion provisoire"
    )

    if conclusion_marker not in report:
        raise RuntimeError(
            "Section Conclusion provisoire introuvable."
        )

    report = report.replace(
        conclusion_marker,
        section + conclusion_marker,
        1,
    )

REPORT_FILE.write_text(
    report,
    encoding="utf-8",
)

print("=" * 78)
print("ANALYSE U21 VERS OPEN INTEGREE")
print("=" * 78)
print("Cohorte U21       :", cohort_total)
print("Passages en Open  :", open_total)
print(
    "Taux de passage  :",
    f"{open_rate:.1f} %",
)
print("Non retrouves     :", disappeared)
print("Autre continuite  :", other)
print("Figure             :", FIGURE_FILE)
print("Note mise a jour   :", REPORT_FILE)

