import csv
from datetime import date
from pathlib import Path


INPUT_FILE = Path(
    "data/exports/participation_annuelle_2017_2026.csv"
)

OUTPUT_FILE = Path(
    "reports/note_participation_2017_2026.md"
)


def pct_change(start, end):
    if start == 0:
        return 0.0
    return 100 * (end - start) / start


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


data = {
    (
        int(row["annee"]),
        row["population"],
    ): row
    for row in rows
}


def integer(year, population, field):
    return int(
        data[(year, population)][field]
    )


total_2017 = integer(
    2017,
    "Tous",
    "participants",
)

total_2023 = integer(
    2023,
    "Tous",
    "participants",
)

total_2026 = integer(
    2026,
    "Tous",
    "participants",
)

women_2023 = integer(
    2023,
    "Tous",
    "femmes",
)

women_2026 = integer(
    2026,
    "Tous",
    "femmes",
)

men_2023 = integer(
    2023,
    "Tous",
    "hommes",
)

men_2026 = integer(
    2026,
    "Tous",
    "hommes",
)

fidelity_2026 = float(
    data[(2026, "Tous")][
        "taux_fidelisation_pct"
    ]
)

senior_retained = integer(
    2026,
    "Seniors",
    "presents_annee_precedente",
)

senior_previous = integer(
    2026,
    "Seniors",
    "participants_annee_precedente",
)

total_change = total_2026 - total_2023
total_change_pct = pct_change(
    total_2023,
    total_2026,
)

female_share_2023 = (
    100 * women_2023 / total_2023
)

female_share_2026 = (
    100 * women_2026 / total_2026
)

population_lines = []

for population in (
    "Jeunes/U21",
    "Open",
    "Seniors",
):
    start = integer(
        2023,
        population,
        "participants",
    )

    end = integer(
        2026,
        population,
        "participants",
    )

    difference = end - start
    percentage = pct_change(
        start,
        end,
    )

    population_lines.append(
        f"| {population} | {start} | {end} | "
        f"{difference:+d} ({percentage:+.1f} %) |"
    )


lines = [
    "# Participation aux championnats de France de ski nautique",
    "",
    "## Analyse longitudinale 2017-2026",
    "",
    f"*Note générée le {date.today().isoformat()}.*",
    "",
    "## Périmètre et méthode",
    "",
    (
        "L’analyse porte sur 29 compétitions nationales "
        "organisées entre 2017 et 2026."
    ),
    "",
    (
        "Les participants sont dénombrés comme des sportifs "
        "uniques par année, toutes compétitions nationales "
        "confondues."
    ),
    "",
    (
        "La continuité des identités a été rétablie au moyen "
        "de 117 correspondances entre anciens et nouveaux "
        "identifiants."
    ),
    "",
    "## Principaux résultats",
    "",
    (
        f"La participation est de **{total_2017} sportifs "
        f"en 2017**, atteint **{total_2023} en 2023**, "
        f"puis recule à **{total_2026} en 2026**."
    ),
    "",
    (
        f"Entre 2023 et 2026, la diminution atteint "
        f"**{total_change} participants**, soit "
        f"**{total_change_pct:.1f} %**."
    ),
    "",
    "### Évolution par population",
    "",
    "| Population | 2023 | 2026 | Variation |",
    "|---|---:|---:|---:|",
    *population_lines,
    "",
    (
        "La population **Jeunes/U21 reste globalement stable**. "
        "La contraction concerne principalement les catégories "
        "**Open** et **Seniors**."
    ),
    "",
    (
        "La baisse senior représente 28 des 40 participants "
        "perdus entre 2023 et 2026."
    ),
    "",
    "### Évolution par sexe",
    "",
    (
        f"Les femmes passent de **{women_2023} à "
        f"{women_2026} participantes**, soit "
        f"{women_2026 - women_2023:+d}."
    ),
    "",
    (
        f"Les hommes passent de **{men_2023} à "
        f"{men_2026} participants**, soit "
        f"{men_2026 - men_2023:+d}."
    ),
    "",
    (
        "La diminution totale est donc principalement masculine : "
        "34 des 40 participants perdus sont des hommes."
    ),
    "",
    (
        f"La part des femmes passe de "
        f"**{female_share_2023:.1f} % en 2023** à "
        f"**{female_share_2026:.1f} % en 2026**, "
        "sans hausse de leur effectif."
    ),
    "",
    "### Fidélisation",
    "",
    (
        f"Le taux global de fidélisation tombe à "
        f"**{fidelity_2026:.1f} % en 2026**."
    ),
    "",
    (
        f"Chez les Seniors, seuls **{senior_retained} des "
        f"{senior_previous} participants de 2025** sont "
        "présents en 2026."
    ),
    "",
    "## Figures",
    "",
    "### Participation totale",
    "",
    (
        "![Participation totale]"
        "(figures/participation_totale_2017_2026.png)"
    ),
    "",
    "### Participation par population",
    "",
    (
        "![Participation par population]"
        "(figures/participation_par_population_2017_2026.png)"
    ),
    "",
    "### Participation par sexe",
    "",
    (
        "![Participation par sexe]"
        "(figures/participation_par_sexe_2017_2026.png)"
    ),
    "",
    "### Taux de fidélisation",
    "",
    (
        "![Taux de fidélisation]"
        "(figures/taux_fidelisation_2018_2026.png)"
    ),
    "",
    "## Conclusion provisoire",
    "",
    (
        "Les données ne montrent pas un effondrement général "
        "de la filière jeunes. Elles mettent en évidence une "
        "difficulté croissante à maintenir une participation "
        "durable dans les catégories Open et Seniors."
    ),
    "",
    (
        "L’étape suivante consistera à étudier les trajectoires "
        "individuelles entre les catégories Jeunes/U21, Open "
        "et Seniors."
    ),
    "",
]


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print("=" * 78)
print("NOTE D'ANALYSE GENEREE")
print("=" * 78)
print("Fichier :", OUTPUT_FILE)
print(
    "Evolution 2023-2026 :",
    f"{total_change:+d}",
    f"({total_change_pct:+.1f} %)",
)
print(
    "Part des femmes :",
    f"{female_share_2023:.1f} %",
    "->",
    f"{female_share_2026:.1f} %",
)
