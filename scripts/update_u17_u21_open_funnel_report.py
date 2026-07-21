"""Integre l'entonnoir individuel U17-U21-Open dans la note."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


INPUT_FILE = Path(
    "data/exports/entonnoir_u17_u21_open_2017_2020.csv"
)

REPORT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/entonnoir_u17_u21_open_2017_2020.png"
)

START_MARKER = "<!-- BEGIN ENTONNOIR U17 U21 OPEN -->"
END_MARKER = "<!-- END ENTONNOIR U17 U21 OPEN -->"


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

women = [
    row
    for row in rows
    if row["sexe"] == "F"
]

men = [
    row
    for row in rows
    if row["sexe"] == "M"
]

women_u21 = sum(
    row["issue"] in (
        "u21_sans_open",
        "u21_puis_open",
    )
    for row in women
)

women_open = sum(
    row["issue"] == "u21_puis_open"
    for row in women
)

men_u21 = sum(
    row["issue"] in (
        "u21_sans_open",
        "u21_puis_open",
    )
    for row in men
)

men_open = sum(
    row["issue"] == "u21_puis_open"
    for row in men
)


labels = [
    "Sorties de U17",
    "Passage en U21",
    "Passage en Open",
]

values = [
    cohort,
    reached_u21,
    reached_open,
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(figsize=(9, 6))
plt.bar(labels, values)

plt.title(
    "Entonnoir individuel U17 → U21 → Open"
)
plt.ylabel("Nombre de sportifs")
plt.ylim(0, max(values) + 5)
plt.grid(axis="y", alpha=0.3)

for index, value in enumerate(values):
    plt.text(
        index,
        value + 0.5,
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
    "## Un entonnoir compétitif extrêmement étroit",
    "",
    (
        "Pour suivre une même population sur l’ensemble du "
        "parcours, l’analyse retient les **32 sportifs dont "
        "la dernière saison observée en U17 se situe entre "
        "2017 et 2020**."
    ),
    "",
    (
        f"Parmi ces **{cohort} sportifs**, seuls "
        f"**{reached_u21} sont ensuite retrouvés en U21** "
        "dans un délai maximal de trois ans."
    ),
    "",
    (
        f"Parmi la cohorte initiale, seuls "
        f"**{reached_open} sportifs sont finalement retrouvés "
        "en Open après leur passage en U21**."
    ),
    "",
    "| Étape observée | Sportifs |",
    "|---|---:|",
    f"| Dernière saison U17 | {cohort} |",
    f"| Passage en U21 | {reached_u21} |",
    f"| Passage en Open après U21 | {reached_open} |",
    "",
    (
        f"Le parcours complet U17 → U21 → Open concerne donc "
        f"**{reached_open} sportifs sur {cohort}**."
    ),
    "",
    (
        f"Une seule personne représente ici "
        f"**{100 / cohort:.1f} points de pourcentage**. "
        "Le pourcentage correspondant ne doit donc jamais "
        "être présenté sans les effectifs bruts."
    ),
    "",
    "### Lecture par sexe",
    "",
    (
        f"Chez les femmes, la cohorte ne comprend que "
        f"**{len(women)} sportives** : "
        f"**{women_u21} atteignent U21** et "
        f"**{women_open} atteignent ensuite Open**."
    ),
    "",
    (
        f"Chez les hommes, la cohorte comprend "
        f"**{len(men)} sportifs** : "
        f"**{men_u21} atteignent U21** et "
        f"**{men_open} atteignent ensuite Open**."
    ),
    "",
    (
        "Ces nombres sont trop faibles pour conclure à une "
        "différence statistiquement robuste entre les sexes."
    ),
    "",
    (
        "![Entonnoir U17 vers U21 puis Open]"
        "(figures/entonnoir_u17_u21_open_2017_2020.png)"
    ),
    "",
    "### Portée institutionnelle",
    "",
    (
        "Cet entonnoir doit être rapproché de la taille déjà "
        "très faible des catégories nationales. L’Open ne "
        "réunit qu’un effectif médian de vingt participants "
        "sur la période 2017-2026."
    ),
    "",
    (
        "La participation aux Championnats de France étant "
        "libre, sans sélection préalable, ces faibles nombres "
        "ne correspondent pas à une élite restreinte par des "
        "quotas. Ils révèlent l’étroitesse réelle du vivier "
        "compétitif national et sa difficulté à conserver les "
        "sportifs au fil des catégories."
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
print("ENTONNOIR INTEGRE AU RAPPORT")
print("=" * 82)
print("Sorties U17       :", cohort)
print("Passages U21      :", reached_u21)
print("Passages Open     :", reached_open)
print(
    "Femmes            :",
    f"{len(women)} -> {women_u21} -> {women_open}",
)
print(
    "Hommes            :",
    f"{len(men)} -> {men_u21} -> {men_open}",
)
print("Figure            :", FIGURE_FILE)
print("Note mise a jour  :", REPORT_FILE)
